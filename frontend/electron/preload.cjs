const { contextBridge, ipcRenderer } = require("electron");

function readArg(prefix, fallback = "") {
  const entry = process.argv.find((value) => value.startsWith(prefix));
  return entry ? entry.slice(prefix.length) : fallback;
}

contextBridge.exposeInMainWorld("grandpaDesktop", {
  platform: process.platform,
  packaged: process.env.NODE_ENV === "production",
  apiBase: readArg("--grandpa-api-base=", "http://127.0.0.1:8765"),
  configPath: readArg("--grandpa-config-path=", ""),
  getRuntime: () => ipcRenderer.invoke("grandpa-desktop:get-runtime"),
  openLogs: () => ipcRenderer.invoke("grandpa-desktop:open-logs"),
  restartBackend: () => ipcRenderer.invoke("grandpa-desktop:restart-backend"),
  onRuntimeUpdate: (callback) => {
    if (typeof callback !== "function") {
      return () => {};
    }
    const handler = (_event, payload) => callback(payload);
    ipcRenderer.on("grandpa-desktop:runtime", handler);
    return () => ipcRenderer.removeListener("grandpa-desktop:runtime", handler);
  },
});
