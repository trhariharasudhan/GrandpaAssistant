const fs = require("fs");
const path = require("path");

const { app } = require("electron");

const DEFAULT_CONFIG = {
  apiHost: "127.0.0.1",
  preferredApiPort: 8765,
  maxPortScan: 6,
  remoteAccessEnabled: true,
  remoteBindHost: "0.0.0.0",
  autoStart: false,
  startHiddenToTray: false,
  minimizeToTray: true,
  restartBackendOnFailure: true,
  backendLaunchTimeoutMs: 45000,
  debugMode: false,
  openDevTools: false,
};

function getDesktopConfigPath() {
  return path.join(app.getPath("userData"), "desktop-config.json");
}

function sanitizeConfig(raw) {
  const source = raw && typeof raw === "object" ? raw : {};
  const preferredApiPort = Number.isFinite(Number(source.preferredApiPort)) ? Math.max(1024, Math.min(65535, Number(source.preferredApiPort))) : DEFAULT_CONFIG.preferredApiPort;
  const maxPortScan = Number.isFinite(Number(source.maxPortScan)) ? Math.max(0, Math.min(25, Number(source.maxPortScan))) : DEFAULT_CONFIG.maxPortScan;
  const backendLaunchTimeoutMs = Number.isFinite(Number(source.backendLaunchTimeoutMs))
    ? Math.max(5000, Math.min(120000, Number(source.backendLaunchTimeoutMs)))
    : DEFAULT_CONFIG.backendLaunchTimeoutMs;

  return {
    apiHost: typeof source.apiHost === "string" && source.apiHost.trim() ? source.apiHost.trim() : DEFAULT_CONFIG.apiHost,
    preferredApiPort,
    maxPortScan,
    remoteAccessEnabled: source.remoteAccessEnabled !== undefined ? Boolean(source.remoteAccessEnabled) : DEFAULT_CONFIG.remoteAccessEnabled,
    remoteBindHost:
      typeof source.remoteBindHost === "string" && source.remoteBindHost.trim()
        ? source.remoteBindHost.trim()
        : DEFAULT_CONFIG.remoteBindHost,
    autoStart: Boolean(source.autoStart),
    startHiddenToTray: Boolean(source.startHiddenToTray),
    minimizeToTray: source.minimizeToTray !== undefined ? Boolean(source.minimizeToTray) : DEFAULT_CONFIG.minimizeToTray,
    restartBackendOnFailure: source.restartBackendOnFailure !== undefined ? Boolean(source.restartBackendOnFailure) : DEFAULT_CONFIG.restartBackendOnFailure,
    backendLaunchTimeoutMs,
    debugMode: Boolean(source.debugMode),
    openDevTools: Boolean(source.openDevTools),
  };
}

function loadDesktopConfig() {
  const configPath = getDesktopConfigPath();
  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  if (!fs.existsSync(configPath)) {
    const config = sanitizeConfig(DEFAULT_CONFIG);
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf8");
    return config;
  }

  try {
    const payload = JSON.parse(fs.readFileSync(configPath, "utf8"));
    const config = sanitizeConfig(payload);
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf8");
    return config;
  } catch (_error) {
    const config = sanitizeConfig(DEFAULT_CONFIG);
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf8");
    return config;
  }
}

function saveDesktopConfig(patch) {
  const current = loadDesktopConfig();
  const next = sanitizeConfig({ ...current, ...(patch || {}) });
  fs.writeFileSync(getDesktopConfigPath(), JSON.stringify(next, null, 2), "utf8");
  return next;
}

module.exports = {
  DEFAULT_CONFIG,
  getDesktopConfigPath,
  loadDesktopConfig,
  saveDesktopConfig,
};
