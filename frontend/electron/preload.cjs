const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("grandpaDesktop", {
  platform: process.platform,
  packaged: process.env.NODE_ENV === "production",
});
