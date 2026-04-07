const { app, BrowserWindow, Menu, Tray, nativeImage, shell, ipcMain } = require("electron");
const path = require("path");

const backendManager = require("./backendManager.cjs");
const { getDesktopConfigPath, loadDesktopConfig, saveDesktopConfig } = require("./config.cjs");

const isDev = !app.isPackaged;
const devUrl = "http://127.0.0.1:4173";
const iconPath = path.join(__dirname, "..", "assets", "app-icon.png");

let mainWindow = null;
let tray = null;
let isQuitting = false;
let desktopConfig = null;

if (!app.requestSingleInstanceLock()) {
  app.quit();
}

app.on("second-instance", () => {
  showMainWindow();
});

function resolvedApiBase() {
  return backendManager.getApiBase() || "http://127.0.0.1:8765";
}

function shouldStartHidden() {
  return app.commandLine.hasSwitch("tray") || Boolean(desktopConfig?.startHiddenToTray);
}

function applyStartupSettings() {
  if (process.platform !== "win32") {
    return;
  }
  app.setLoginItemSettings({
    openAtLogin: Boolean(desktopConfig?.autoStart),
    path: process.execPath,
    args: desktopConfig?.startHiddenToTray ? ["--tray"] : [],
  });
}

function createWindow() {
  const startHidden = shouldStartHidden();
  const window = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 720,
    show: !startHidden,
    backgroundColor: "#fafafb",
    title: "Grandpa Assistant",
    icon: iconPath,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: [
        `--grandpa-api-base=${resolvedApiBase()}`,
        `--grandpa-config-path=${getDesktopConfigPath()}`,
      ],
    },
  });

  window.on("close", (event) => {
    if (isQuitting || !desktopConfig?.minimizeToTray) {
      return;
    }
    event.preventDefault();
    window.hide();
  });

  if (isDev) {
    window.loadURL(devUrl);
    if (desktopConfig?.openDevTools) {
      window.webContents.openDevTools({ mode: "detach" });
    }
  } else {
    window.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  return window;
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    mainWindow = createWindow();
  }
  mainWindow.show();
  mainWindow.focus();
}

function toggleMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    showMainWindow();
    return;
  }
  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    showMainWindow();
  }
}

function openLogsFolder() {
  const target = backendManager.getLogsRoot();
  return shell.openPath(target);
}

async function restartManagedBackend() {
  const result = await backendManager.restartBackend(desktopConfig);
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("grandpa-desktop:runtime", {
      apiBase: result.apiBase,
      backend: backendManager.getBackendState(),
    });
  }
  rebuildTrayMenu();
  return result;
}

function rebuildTrayMenu() {
  if (!tray) {
    return;
  }
  const backendState = backendManager.getBackendState();
  const template = [
    {
      label: mainWindow && mainWindow.isVisible() ? "Hide Assistant" : "Open Assistant",
      click: () => toggleMainWindow(),
    },
    {
      label: backendState.running ? "Restart Backend" : "Start Backend",
      click: async () => {
        if (backendState.running) {
          await restartManagedBackend();
        } else {
          await backendManager.ensureBackend(desktopConfig);
          rebuildTrayMenu();
        }
      },
    },
    {
      label: "Open Logs Folder",
      click: () => openLogsFolder(),
    },
    { type: "separator" },
    {
      label: "Launch On Startup",
      type: "checkbox",
      checked: Boolean(desktopConfig?.autoStart),
      click: () => {
        desktopConfig = saveDesktopConfig({ autoStart: !desktopConfig?.autoStart });
        applyStartupSettings();
        rebuildTrayMenu();
      },
    },
    {
      label: "Start Hidden To Tray",
      type: "checkbox",
      checked: Boolean(desktopConfig?.startHiddenToTray),
      click: () => {
        desktopConfig = saveDesktopConfig({ startHiddenToTray: !desktopConfig?.startHiddenToTray });
        applyStartupSettings();
        rebuildTrayMenu();
      },
    },
    {
      label: "Minimize To Tray",
      type: "checkbox",
      checked: Boolean(desktopConfig?.minimizeToTray),
      click: () => {
        desktopConfig = saveDesktopConfig({ minimizeToTray: !desktopConfig?.minimizeToTray });
        rebuildTrayMenu();
      },
    },
    { type: "separator" },
    {
      label: "Quit Grandpa Assistant",
      click: async () => {
        isQuitting = true;
        await backendManager.stopBackend();
        app.quit();
      },
    },
  ];
  tray.setContextMenu(Menu.buildFromTemplate(template));
}

function createTray() {
  if (tray) {
    return tray;
  }
  const image = nativeImage.createFromPath(iconPath);
  tray = new Tray(image);
  tray.setToolTip("Grandpa Assistant");
  tray.on("double-click", () => showMainWindow());
  tray.on("click", () => toggleMainWindow());
  rebuildTrayMenu();
  return tray;
}

ipcMain.handle("grandpa-desktop:get-runtime", () => ({
  apiBase: resolvedApiBase(),
  configPath: getDesktopConfigPath(),
  backend: backendManager.getBackendState(),
  config: desktopConfig,
}));

ipcMain.handle("grandpa-desktop:open-logs", async () => {
  await openLogsFolder();
  return { ok: true };
});

ipcMain.handle("grandpa-desktop:restart-backend", async () => {
  const result = await restartManagedBackend();
  return { ok: true, apiBase: result.apiBase, backend: backendManager.getBackendState() };
});

app.whenReady().then(async () => {
  desktopConfig = loadDesktopConfig();
  applyStartupSettings();
  createTray();

  try {
    await backendManager.ensureBackend(desktopConfig);
  } catch (error) {
    console.error("Failed to start Grandpa backend:", error);
  }

  mainWindow = createWindow();
  if (!shouldStartHidden()) {
    showMainWindow();
  }

  app.on("activate", () => {
    showMainWindow();
  });
});

app.on("before-quit", () => {
  isQuitting = true;
});

app.on("will-quit", async (event) => {
  if (!backendManager.isStopping()) {
    event.preventDefault();
    isQuitting = true;
    await backendManager.stopBackend();
    app.exit(0);
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin" && !desktopConfig?.minimizeToTray) {
    app.quit();
  }
});
