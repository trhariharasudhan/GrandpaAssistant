const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");
const { spawn } = require("child_process");

const { app } = require("electron");

const projectRoot = path.join(__dirname, "..", "..");

let backendProcess = null;
let backendState = {
  running: false,
  managed: false,
  mode: "",
  port: null,
  apiBase: "",
  lastExitCode: null,
  lastExitSignal: null,
  logPath: "",
};
let lastConfig = null;
let restartTimer = null;
let restartAttempts = 0;
let stopping = false;

function getLogsRoot() {
  if (app.isPackaged) {
    return path.join(process.env.LOCALAPPDATA || app.getPath("userData"), "GrandpaAssistant");
  }
  return path.join(projectRoot, "backend", "logs");
}

function ensureLogsRoot() {
  const logRoot = getLogsRoot();
  fs.mkdirSync(logRoot, { recursive: true });
  return logRoot;
}

function supervisorLogPath() {
  return path.join(ensureLogsRoot(), "desktop-supervisor.log");
}

function logSupervisor(message) {
  const line = `[${new Date().toISOString()}] ${message}`;
  fs.appendFileSync(supervisorLogPath(), line + "\n", "utf8");
}

function resolvePython() {
  const candidates = [
    path.join(projectRoot, ".python311", "python.exe"),
    path.join(projectRoot, ".venv", "Scripts", "python.exe"),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || "python";
}

function resolveBackendExecutable() {
  if (!app.isPackaged) {
    return null;
  }
  const candidates = [
    path.join(process.resourcesPath, "backend", "GrandpaAssistantBackend", "GrandpaAssistantBackend.exe"),
    path.join(process.resourcesPath, "backend", "GrandpaAssistantBackend.exe"),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function resolveBackendLaunch() {
  const backendExe = resolveBackendExecutable();
  if (backendExe) {
    return {
      command: backendExe,
      args: [],
      cwd: path.dirname(backendExe),
      mode: "packaged-exe",
    };
  }

  return {
    command: resolvePython(),
    args: [path.join(projectRoot, "backend", "desktop_backend_entry.py")],
    cwd: projectRoot,
    mode: "python",
  };
}

function requestJson(host, port, route = "/api/health", timeoutMs = 1500) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host,
        port,
        path: route,
        method: "GET",
        timeout: timeoutMs,
      },
      (res) => {
        let raw = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          raw += chunk;
        });
        res.on("end", () => {
          try {
            const payload = raw ? JSON.parse(raw) : {};
            resolve({ statusCode: res.statusCode || 0, payload });
          } catch (error) {
            reject(error);
          }
        });
      }
    );
    req.on("timeout", () => {
      req.destroy(new Error("timeout"));
    });
    req.on("error", reject);
    req.end();
  });
}

function backendBindHost(config) {
  if (config?.remoteAccessEnabled) {
    return config.remoteBindHost || "0.0.0.0";
  }
  return config?.apiHost || "127.0.0.1";
}

async function isAssistantRunning(host, port) {
  try {
    const response = await requestJson(host, port, "/api/health", 1200);
    return response.statusCode === 200 && Boolean(response.payload?.ok);
  } catch (_error) {
    return false;
  }
}

function isPortAvailable(host, port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, host);
  });
}

async function resolveBackendPort(config) {
  const host = config.apiHost || "127.0.0.1";
  const bindHost = backendBindHost(config);
  const preferred = Number(config.preferredApiPort || 8765);
  const maxPortScan = Number(config.maxPortScan || 6);
  for (let offset = 0; offset <= maxPortScan; offset += 1) {
    const candidate = preferred + offset;
    if (await isAssistantRunning(host, candidate)) {
      return { host, bindHost, port: candidate, reuseExisting: true };
    }
    if (await isPortAvailable(bindHost, candidate)) {
      return { host, bindHost, port: candidate, reuseExisting: false };
    }
  }
  throw new Error("Could not find a free backend port for Grandpa Assistant.");
}

function apiBaseFor(host, port) {
  return `http://${host}:${port}`;
}

function updateState(patch) {
  backendState = { ...backendState, ...(patch || {}) };
  return backendState;
}

function spawnBackend(port, config, bindHost) {
  const launch = resolveBackendLaunch();
  const env = {
    ...process.env,
    GRANDPA_ASSISTANT_HOST: bindHost || backendBindHost(config),
    GRANDPA_ASSISTANT_PORT: String(port),
    GRANDPA_ASSISTANT_LOG_LEVEL: config.debugMode ? "info" : "warning",
    GRANDPA_DESKTOP_EXE: app.isPackaged ? process.execPath : "",
  };

  logSupervisor(`Starting backend in ${launch.mode} mode on port ${port}.`);
  backendProcess = spawn(launch.command, launch.args, {
    cwd: launch.cwd,
    env,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  updateState({
    running: true,
    managed: true,
    mode: launch.mode,
    port,
    apiBase: apiBaseFor(config.apiHost || "127.0.0.1", port),
    logPath: supervisorLogPath(),
  });

  if (backendProcess.stdout) {
    backendProcess.stdout.on("data", (chunk) => {
      logSupervisor(`backend stdout: ${String(chunk).trim()}`);
    });
  }
  if (backendProcess.stderr) {
    backendProcess.stderr.on("data", (chunk) => {
      logSupervisor(`backend stderr: ${String(chunk).trim()}`);
    });
  }

  backendProcess.on("exit", (code, signal) => {
    logSupervisor(`Backend exited with code=${code} signal=${signal}`);
    updateState({
      running: false,
      lastExitCode: code,
      lastExitSignal: signal,
    });
    backendProcess = null;

    if (!stopping && lastConfig?.restartBackendOnFailure) {
      const delay = Math.min(30000, 1000 * Math.max(1, restartAttempts + 1));
      restartAttempts += 1;
      restartTimer = setTimeout(() => {
        ensureBackend(lastConfig).catch((error) => {
          logSupervisor(`Backend restart failed: ${error.message}`);
        });
      }, delay);
    }
  });
}

async function waitForBackendReady(host, port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await isAssistantRunning(host, port)) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 750));
  }
  return false;
}

async function ensureBackend(config) {
  lastConfig = config;
  stopping = false;
  const resolved = await resolveBackendPort(config);
  updateState({
    port: resolved.port,
    apiBase: apiBaseFor(resolved.host, resolved.port),
    logPath: supervisorLogPath(),
  });

  if (resolved.reuseExisting) {
    logSupervisor(`Reusing existing backend on port ${resolved.port}.`);
    updateState({
      running: true,
      managed: false,
      mode: "external",
    });
    return { apiBase: backendState.apiBase, reused: true };
  }

  spawnBackend(resolved.port, config, resolved.bindHost);
  const ready = await waitForBackendReady(resolved.host, resolved.port, Number(config.backendLaunchTimeoutMs || 45000));
  if (!ready) {
    await stopBackend();
    throw new Error("Grandpa Assistant backend did not become ready in time.");
  }
  restartAttempts = 0;
  return { apiBase: backendState.apiBase, reused: false };
}

async function stopBackend() {
  stopping = true;
  if (restartTimer) {
    clearTimeout(restartTimer);
    restartTimer = null;
  }
  if (!backendProcess) {
    updateState({ running: false });
    return;
  }
  const processRef = backendProcess;
  backendProcess = null;
  await new Promise((resolve) => {
    processRef.once("exit", () => resolve());
    try {
      processRef.kill();
    } catch (_error) {
      resolve();
    }
    setTimeout(resolve, 3000);
  });
  updateState({ running: false });
}

async function restartBackend(config) {
  await stopBackend();
  return ensureBackend(config || lastConfig || {});
}

function getApiBase() {
  return backendState.apiBase;
}

function getBackendState() {
  return { ...backendState };
}

function isStopping() {
  return stopping;
}

module.exports = {
  ensureBackend,
  stopBackend,
  restartBackend,
  getApiBase,
  getBackendState,
  getLogsRoot,
  isStopping,
};
