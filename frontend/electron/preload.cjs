const { contextBridge } = require("electron");
contextBridge.exposeInMainWorld("novaDesktop", { isDesktop: true });
