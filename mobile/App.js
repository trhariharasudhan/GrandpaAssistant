import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as FileSystem from "expo-file-system";
import { Audio } from "expo-av";
import { StatusBar } from "expo-status-bar";


const STORAGE_KEYS = {
  serverUrl: "grandpa-mobile-server-url",
  token: "grandpa-mobile-token",
  device: "grandpa-mobile-device",
};


function normalizeServerUrl(value) {
  const text = String(value || "").trim().replace(/\/+$/, "");
  if (!text) {
    return "";
  }
  if (/^https?:\/\//i.test(text)) {
    return text;
  }
  return `http://${text}`;
}


function wsUrl(serverUrl, token) {
  const normalized = normalizeServerUrl(serverUrl);
  if (!normalized || !token) {
    return "";
  }
  const base = normalized.replace(/^http/i, "ws");
  return `${base}/mobile/ws?token=${encodeURIComponent(token)}`;
}


async function fetchJson(serverUrl, path, options = {}, token = "") {
  const headers = {
    Accept: "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${normalizeServerUrl(serverUrl)}${path}`, {
    ...options,
    headers,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.ok === false) {
    throw new Error(payload?.detail || payload?.message || "Request failed.");
  }
  return payload;
}


function Bubble({ item }) {
  const isUser = item.role === "user";
  return (
    <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
      <Text style={[styles.bubbleRole, isUser ? styles.userBubbleRole : styles.assistantBubbleRole]}>
        {isUser ? "You" : "Grandpa"}
      </Text>
      <Text style={[styles.bubbleText, isUser ? styles.userBubbleText : styles.assistantBubbleText]}>
        {item.text}
      </Text>
    </View>
  );
}


export default function App() {
  const [serverUrl, setServerUrl] = useState("http://192.168.1.20:8765");
  const [pairCode, setPairCode] = useState("");
  const [deviceName, setDeviceName] = useState("My Phone");
  const [token, setToken] = useState("");
  const [device, setDevice] = useState(null);
  const [busy, setBusy] = useState(true);
  const [linking, setLinking] = useState(false);
  const [tab, setTab] = useState("chat");
  const [input, setInput] = useState("");
  const [commandInput, setCommandInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState("");
  const [socketState, setSocketState] = useState("disconnected");
  const [isRecording, setIsRecording] = useState(false);
  const [requestError, setRequestError] = useState("");
  const websocketRef = useRef(null);
  const lastEventSeqRef = useRef(0);
  const recordingRef = useRef(null);
  const listRef = useRef(null);

  const headerText = useMemo(() => {
    if (!device) {
      return "Link your phone to Grandpa Assistant";
    }
    return `${device.name || "Mobile"}${socketState === "connected" ? " · Live" : " · Offline"}`;
  }, [device, socketState]);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      try {
        const [savedUrl, savedToken, savedDevice] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEYS.serverUrl),
          AsyncStorage.getItem(STORAGE_KEYS.token),
          AsyncStorage.getItem(STORAGE_KEYS.device),
        ]);
        if (!active) {
          return;
        }
        if (savedUrl) {
          setServerUrl(savedUrl);
        }
        if (savedToken) {
          setToken(savedToken);
          try {
            const payload = await fetchJson(savedUrl || serverUrl, "/mobile/auth/token", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: savedToken }),
            });
            if (!active) {
              return;
            }
            setDevice(payload.device || (savedDevice ? JSON.parse(savedDevice) : null));
          } catch (_error) {
            await AsyncStorage.multiRemove([STORAGE_KEYS.token, STORAGE_KEYS.device]);
          }
        }
      } finally {
        if (active) {
          setBusy(false);
        }
      }
    }

    bootstrap();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!token || !device) {
      if (websocketRef.current) {
        websocketRef.current.close();
        websocketRef.current = null;
      }
      setSocketState("disconnected");
      return undefined;
    }

    const url = wsUrl(serverUrl, token);
    if (!url) {
      return undefined;
    }

    const socket = new WebSocket(url);
    websocketRef.current = socket;
    setSocketState("connecting");

    socket.onopen = () => {
      setSocketState("connected");
      setRequestError("");
    };

    socket.onclose = () => {
      setSocketState("disconnected");
    };

    socket.onerror = () => {
      setSocketState("error");
    };

    socket.onmessage = async (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "ready") {
          setDashboard(payload.dashboard || null);
          return;
        }
        if (payload.type === "status") {
          setDashboard(payload.dashboard || null);
          return;
        }
        if (payload.type === "event" && payload.event) {
          const seq = Number(payload.event.seq || 0);
          if (seq <= lastEventSeqRef.current) {
            return;
          }
          lastEventSeqRef.current = seq;
          const eventType = String(payload.event.type || "");
          const eventPayload = payload.event.payload || {};
          if (eventType === "mobile.notification") {
            setNotifications((current) => [eventPayload, ...current].slice(0, 20));
          }
          if (eventType === "mobile.chat.message") {
            setMessages((current) => {
              const nextItem = {
                id: `${seq}`,
                role: eventPayload.role || "assistant",
                text: eventPayload.text || "",
                session_id: eventPayload.session_id || "",
              };
              const exists = current.some(
                (item) =>
                  item.role === nextItem.role &&
                  item.text === nextItem.text &&
                  item.session_id === nextItem.session_id
              );
              if (exists) {
                return current;
              }
              return [...current, nextItem].slice(-120);
            });
          }
          if (eventType === "mobile.command.result") {
            const firstMessage = (eventPayload.messages || [])[0];
            if (firstMessage) {
              setNotifications((current) => [
                {
                  id: `${seq}-command`,
                  title: "Command Result",
                  body: firstMessage,
                  created_at: payload.event.created_at,
                  level: "info",
                },
                ...current,
              ].slice(0, 20));
            }
          }
          return;
        }
        if (payload.type === "chat.result" && payload.result) {
          await applyChatResponse(payload.result);
          return;
        }
        if (payload.type === "command.result" && payload.result) {
          const firstMessage = (payload.result.messages || [])[0];
          if (firstMessage) {
            setNotifications((current) => [
              {
                id: `cmd-${Date.now()}`,
                title: "Command Result",
                body: firstMessage,
                created_at: new Date().toISOString(),
                level: "info",
              },
              ...current,
            ].slice(0, 20));
          }
        }
      } catch (_error) {
        // Ignore malformed socket payloads and keep the session alive.
      }
    };

    return () => {
      socket.close();
      websocketRef.current = null;
    };
  }, [token, device, serverUrl]);

  useEffect(() => {
    if (!token || !device) {
      return;
    }
    refreshMobileState();
  }, [token, device]);

  useEffect(() => {
    listRef.current?.scrollToEnd?.({ animated: true });
  }, [messages]);

  async function persistSession(nextServerUrl, nextToken, nextDevice) {
    await AsyncStorage.multiSet([
      [STORAGE_KEYS.serverUrl, normalizeServerUrl(nextServerUrl)],
      [STORAGE_KEYS.token, nextToken],
      [STORAGE_KEYS.device, JSON.stringify(nextDevice || {})],
    ]);
  }

  async function clearSession() {
    await AsyncStorage.multiRemove([STORAGE_KEYS.serverUrl, STORAGE_KEYS.token, STORAGE_KEYS.device]);
    setToken("");
    setDevice(null);
    setMessages([]);
    setNotifications([]);
    setDashboard(null);
    setSessions([]);
    setCurrentSessionId("");
  }

  async function refreshMobileState() {
    try {
      const [dashboardPayload, notificationsPayload, sessionsPayload] = await Promise.all([
        fetchJson(serverUrl, "/mobile/dashboard", {}, token),
        fetchJson(serverUrl, "/mobile/notifications", {}, token),
        fetchJson(serverUrl, "/mobile/chat/sessions", {}, token),
      ]);
      setDashboard(dashboardPayload.dashboard || null);
      setNotifications(notificationsPayload.items || []);
      setSessions(sessionsPayload.sessions || []);
      if (!currentSessionId && (sessionsPayload.sessions || [])[0]?.id) {
        setCurrentSessionId(sessionsPayload.sessions[0].id);
      }
    } catch (error) {
      setRequestError(error.message || "Could not load mobile state.");
    }
  }

  async function pairDevice() {
    const normalizedUrl = normalizeServerUrl(serverUrl);
    if (!normalizedUrl || !pairCode.trim() || !deviceName.trim()) {
      Alert.alert("Missing details", "Enter the desktop server URL, pairing code, and your device name.");
      return;
    }
    setLinking(true);
    setRequestError("");
    try {
      const payload = await fetchJson(normalizedUrl, "/mobile/pairing/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pair_code: pairCode,
          device_name: deviceName,
          platform: "expo-mobile",
          app_version: "1.0.0",
        }),
      });
      setToken(payload.token);
      setDevice(payload.device);
      await persistSession(normalizedUrl, payload.token, payload.device);
      setPairCode("");
      await refreshMobileState();
    } catch (error) {
      setRequestError(error.message || "Could not pair device.");
    } finally {
      setLinking(false);
    }
  }

  async function playAudioReply(audioBase64) {
    if (!audioBase64) {
      return;
    }
    const targetPath = `${FileSystem.cacheDirectory}grandpa-reply-${Date.now()}.wav`;
    try {
      await FileSystem.writeAsStringAsync(targetPath, audioBase64, {
        encoding: FileSystem.EncodingType.Base64,
      });
      const { sound } = await Audio.Sound.createAsync({ uri: targetPath });
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status?.didJustFinish) {
          sound.unloadAsync().catch(() => {});
          FileSystem.deleteAsync(targetPath, { idempotent: true }).catch(() => {});
        }
      });
      await sound.playAsync();
    } catch (_error) {
      FileSystem.deleteAsync(targetPath, { idempotent: true }).catch(() => {});
    }
  }

  async function applyChatResponse(payload) {
    const replyText = payload.reply || payload.message?.content || "";
    const sessionId = payload.session?.id || currentSessionId;
    if (sessionId && !currentSessionId) {
      setCurrentSessionId(sessionId);
    }
    setMessages((current) => {
      const next = [...current];
      if (payload.message?.role === "assistant" && replyText) {
        next.push({
          id: payload.message?.id || `assistant-${Date.now()}`,
          role: "assistant",
          text: replyText,
          session_id: sessionId,
        });
      }
      return next.slice(-120);
    });
    if (payload.audio_base64) {
      await playAudioReply(payload.audio_base64);
    }
    if (payload.session) {
      setCurrentSessionId(payload.session.id || "");
    }
    await refreshMobileState();
  }

  async function sendChat() {
    const message = input.trim();
    if (!message || !token) {
      return;
    }
    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", text: message, session_id: currentSessionId },
    ]);
    setInput("");
    try {
      const payload = await fetchJson(
        serverUrl,
        "/mobile/chat",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            session_id: currentSessionId || null,
            include_audio: true,
          }),
        },
        token
      );
      await applyChatResponse(payload);
    } catch (error) {
      setRequestError(error.message || "Could not send chat.");
    }
  }

  async function runCommand(command = commandInput) {
    const cleanCommand = String(command || "").trim();
    if (!cleanCommand || !token) {
      return;
    }
    setCommandInput("");
    try {
      const payload = await fetchJson(
        serverUrl,
        "/mobile/command",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: cleanCommand, include_state: true }),
        },
        token
      );
      const firstMessage = (payload.messages || [])[0];
      if (firstMessage) {
        setNotifications((current) => [
          {
            id: `notif-${Date.now()}`,
            title: "Command Result",
            body: firstMessage,
            created_at: new Date().toISOString(),
            level: "info",
          },
          ...current,
        ].slice(0, 20));
      }
      await refreshMobileState();
    } catch (error) {
      setRequestError(error.message || "Could not run remote command.");
    }
  }

  async function startVoiceRecording() {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Alert.alert("Microphone required", "Grant microphone access to send voice to Grandpa Assistant.");
        return;
      }
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
      const recording = new Audio.Recording();
      await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      await recording.startAsync();
      recordingRef.current = recording;
      setIsRecording(true);
    } catch (error) {
      setRequestError(error.message || "Could not start recording.");
    }
  }

  async function stopVoiceRecording() {
    const recording = recordingRef.current;
    if (!recording || !token) {
      return;
    }
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      recordingRef.current = null;
      setIsRecording(false);
      if (!uri) {
        throw new Error("Recording file was not created.");
      }
      const formData = new FormData();
      formData.append("session_id", currentSessionId || "");
      formData.append("include_audio", "true");
      formData.append("file", {
        uri,
        name: "voice-message.m4a",
        type: "audio/m4a",
      });
      const response = await fetch(`${normalizeServerUrl(serverUrl)}/mobile/voice/chat`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.detail || payload?.message || "Voice chat failed.");
      }
      if (payload.transcript) {
        setMessages((current) => [
          ...current,
          { id: `voice-user-${Date.now()}`, role: "user", text: payload.transcript, session_id: currentSessionId },
        ]);
      }
      await applyChatResponse(payload);
    } catch (error) {
      setRequestError(error.message || "Could not send voice message.");
    } finally {
      setIsRecording(false);
    }
  }

  const quickCommands = [
    "plan my day",
    "show tasks",
    "security status",
    "mobile companion status",
    "smart home status",
  ];

  if (busy) {
    return (
      <SafeAreaView style={styles.centeredScreen}>
        <StatusBar style="dark" />
        <ActivityIndicator size="large" color="#0f3d2e" />
        <Text style={styles.loadingText}>Connecting to Grandpa Assistant...</Text>
      </SafeAreaView>
    );
  }

  if (!token || !device) {
    return (
      <SafeAreaView style={styles.screen}>
        <StatusBar style="dark" />
        <ScrollView contentContainerStyle={styles.authContainer}>
          <Text style={styles.brandTitle}>Grandpa Assistant</Text>
          <Text style={styles.brandSubtitle}>Mobile companion and remote control</Text>

          <View style={styles.card}>
            <Text style={styles.label}>Desktop server URL</Text>
            <TextInput
              value={serverUrl}
              onChangeText={setServerUrl}
              style={styles.input}
              placeholder="http://192.168.1.20:8765"
              autoCapitalize="none"
            />

            <Text style={styles.label}>Pairing code</Text>
            <TextInput
              value={pairCode}
              onChangeText={setPairCode}
              style={styles.input}
              placeholder="123456"
              keyboardType="number-pad"
            />

            <Text style={styles.label}>Device name</Text>
            <TextInput
              value={deviceName}
              onChangeText={setDeviceName}
              style={styles.input}
              placeholder="My Phone"
            />

            <Pressable style={styles.primaryButton} onPress={pairDevice} disabled={linking}>
              <Text style={styles.primaryButtonText}>{linking ? "Linking..." : "Pair And Login"}</Text>
            </Pressable>

            <Text style={styles.helperText}>
              Start pairing on the desktop first using: setup mobile companion My Phone
            </Text>
            {!!requestError && <Text style={styles.errorText}>{requestError}</Text>}
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <KeyboardAvoidingView style={styles.flexOne} behavior="padding">
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>{headerText}</Text>
            <Text style={styles.headerSubtext}>
              {dashboard?.status?.assistant_state || "idle"} · {dashboard?.status?.cpu_percent || 0}% CPU ·{" "}
              {dashboard?.status?.ram_percent || 0}% RAM
            </Text>
          </View>
          <Pressable style={styles.secondaryButton} onPress={clearSession}>
            <Text style={styles.secondaryButtonText}>Logout</Text>
          </Pressable>
        </View>

        <View style={styles.tabRow}>
          <Pressable style={[styles.tabButton, tab === "chat" && styles.activeTab]} onPress={() => setTab("chat")}>
            <Text style={[styles.tabText, tab === "chat" && styles.activeTabText]}>Chat</Text>
          </Pressable>
          <Pressable
            style={[styles.tabButton, tab === "dashboard" && styles.activeTab]}
            onPress={() => setTab("dashboard")}
          >
            <Text style={[styles.tabText, tab === "dashboard" && styles.activeTabText]}>Dashboard</Text>
          </Pressable>
        </View>

        {tab === "chat" ? (
          <View style={styles.flexOne}>
            <FlatList
              ref={listRef}
              data={messages}
              keyExtractor={(item, index) => `${item.id || index}`}
              renderItem={({ item }) => <Bubble item={item} />}
              contentContainerStyle={styles.messageList}
            />

            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickRow}>
              {quickCommands.map((command) => (
                <Pressable key={command} style={styles.quickChip} onPress={() => runCommand(command)}>
                  <Text style={styles.quickChipText}>{command}</Text>
                </Pressable>
              ))}
            </ScrollView>

            <View style={styles.commandRow}>
              <TextInput
                value={commandInput}
                onChangeText={setCommandInput}
                style={[styles.input, styles.commandInput]}
                placeholder="Run remote command"
              />
              <Pressable style={styles.secondaryButton} onPress={() => runCommand()}>
                <Text style={styles.secondaryButtonText}>Run</Text>
              </Pressable>
            </View>

            <View style={styles.inputRow}>
              <TextInput
                value={input}
                onChangeText={setInput}
                style={[styles.input, styles.chatInput]}
                placeholder="Message Grandpa Assistant"
                multiline
              />
              <Pressable
                style={[styles.voiceButton, isRecording && styles.voiceButtonActive]}
                onPress={isRecording ? stopVoiceRecording : startVoiceRecording}
              >
                <Text style={styles.voiceButtonText}>{isRecording ? "Stop" : "Voice"}</Text>
              </Pressable>
              <Pressable style={styles.primaryButton} onPress={sendChat}>
                <Text style={styles.primaryButtonText}>Send</Text>
              </Pressable>
            </View>
          </View>
        ) : (
          <ScrollView contentContainerStyle={styles.dashboardScroll}>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Assistant Status</Text>
              <Text style={styles.metricText}>State: {dashboard?.status?.assistant_state || "idle"}</Text>
              <Text style={styles.metricText}>CPU: {dashboard?.status?.cpu_percent || 0}%</Text>
              <Text style={styles.metricText}>RAM: {dashboard?.status?.ram_used_mb || 0} / {dashboard?.status?.ram_total_mb || 0} MB</Text>
              <Text style={styles.metricText}>Linked device: {device?.name || "Unknown"}</Text>
              <Text style={styles.metricText}>Socket: {socketState}</Text>
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Tasks</Text>
              <Text style={styles.metricText}>
                Pending: {dashboard?.tasks?.pending_count || 0}
              </Text>
              {(dashboard?.tasks?.items || []).slice(0, 5).map((item, index) => (
                <Text key={`${item?.id || index}`} style={styles.listText}>
                  {index + 1}. {item?.title || "Task"}
                </Text>
              ))}
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Memory And Mood</Text>
              <Text style={styles.metricText}>Last mood: {dashboard?.memory?.mood?.last_mood || "neutral"}</Text>
              <Text style={styles.metricText}>History count: {dashboard?.memory?.mood?.history_count || 0}</Text>
              <Text style={styles.metricText}>
                Semantic memory: {dashboard?.memory?.semantic?.backend || "local"}
              </Text>
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Notifications</Text>
              {(notifications || []).slice(0, 8).map((item, index) => (
                <View key={`${item.id || index}`} style={styles.notificationItem}>
                  <Text style={styles.notificationTitle}>{item.title || "Update"}</Text>
                  <Text style={styles.notificationBody}>{item.body || ""}</Text>
                </View>
              ))}
            </View>
          </ScrollView>
        )}

        {!!requestError && <Text style={styles.errorText}>{requestError}</Text>}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}


const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#f5f2e8",
  },
  flexOne: {
    flex: 1,
  },
  centeredScreen: {
    flex: 1,
    backgroundColor: "#f5f2e8",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  loadingText: {
    fontSize: 16,
    color: "#173227",
  },
  authContainer: {
    padding: 24,
    gap: 18,
  },
  brandTitle: {
    fontSize: 30,
    fontWeight: "800",
    color: "#173227",
  },
  brandSubtitle: {
    fontSize: 15,
    color: "#4a5a53",
  },
  card: {
    backgroundColor: "#fffaf0",
    borderRadius: 18,
    padding: 18,
    borderWidth: 1,
    borderColor: "#d8ccb2",
    gap: 10,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: "800",
    color: "#173227",
  },
  headerSubtext: {
    marginTop: 4,
    color: "#4a5a53",
    fontSize: 13,
  },
  tabRow: {
    flexDirection: "row",
    paddingHorizontal: 16,
    gap: 10,
    marginBottom: 8,
  },
  tabButton: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 999,
    backgroundColor: "#dfd7c6",
  },
  activeTab: {
    backgroundColor: "#173227",
  },
  tabText: {
    color: "#173227",
    fontWeight: "700",
  },
  activeTabText: {
    color: "#fffaf0",
  },
  messageList: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    gap: 10,
  },
  bubble: {
    maxWidth: "86%",
    padding: 14,
    borderRadius: 18,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "#173227",
  },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: "#fffaf0",
    borderWidth: 1,
    borderColor: "#d8ccb2",
  },
  bubbleRole: {
    fontSize: 11,
    fontWeight: "700",
    marginBottom: 6,
    textTransform: "uppercase",
  },
  userBubbleRole: {
    color: "#d7efe1",
  },
  assistantBubbleRole: {
    color: "#5c6a64",
  },
  bubbleText: {
    fontSize: 15,
    lineHeight: 22,
  },
  userBubbleText: {
    color: "#fffaf0",
  },
  assistantBubbleText: {
    color: "#173227",
  },
  label: {
    fontWeight: "700",
    color: "#173227",
  },
  input: {
    borderWidth: 1,
    borderColor: "#d8ccb2",
    borderRadius: 14,
    backgroundColor: "#fff",
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: "#173227",
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 10,
    padding: 16,
  },
  chatInput: {
    flex: 1,
    minHeight: 52,
    maxHeight: 120,
  },
  commandRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 16,
  },
  commandInput: {
    flex: 1,
  },
  primaryButton: {
    backgroundColor: "#173227",
    borderRadius: 14,
    paddingHorizontal: 18,
    paddingVertical: 14,
    justifyContent: "center",
    alignItems: "center",
  },
  primaryButtonText: {
    color: "#fffaf0",
    fontWeight: "800",
  },
  secondaryButton: {
    backgroundColor: "#dfd7c6",
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 12,
    justifyContent: "center",
    alignItems: "center",
  },
  secondaryButtonText: {
    color: "#173227",
    fontWeight: "800",
  },
  voiceButton: {
    backgroundColor: "#b7c9a8",
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    justifyContent: "center",
    alignItems: "center",
  },
  voiceButtonActive: {
    backgroundColor: "#b24b3f",
  },
  voiceButtonText: {
    color: "#173227",
    fontWeight: "800",
  },
  helperText: {
    color: "#5b695f",
    lineHeight: 20,
  },
  errorText: {
    color: "#a12e28",
    paddingHorizontal: 16,
    paddingBottom: 10,
  },
  quickRow: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 8,
  },
  quickChip: {
    backgroundColor: "#ece4d4",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  quickChipText: {
    color: "#173227",
    fontWeight: "700",
  },
  dashboardScroll: {
    padding: 16,
    gap: 14,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#173227",
    marginBottom: 4,
  },
  metricText: {
    color: "#173227",
    lineHeight: 22,
  },
  listText: {
    color: "#40524a",
    lineHeight: 21,
  },
  notificationItem: {
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: "#ece4d4",
  },
  notificationTitle: {
    fontWeight: "800",
    color: "#173227",
  },
  notificationBody: {
    color: "#4a5a53",
    marginTop: 2,
  },
});
