const { app, BrowserWindow, Tray, Menu, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

const PROJECT = path.resolve(__dirname, "../../");
const BACKEND = path.join(PROJECT, "backend");
const PYTHON = path.join(PROJECT, "venv", "Scripts", "python.exe");
let win, tray, backendProcess, quitting = false;
app.setAppUserModelId("com.nova.personalassistant");

async function backendOnline() {
  try { return (await fetch("http://127.0.0.1:8000/")).ok; }
  catch { return false; }
}
async function startBackend() {
  if (await backendOnline()) return;
  backendProcess = spawn(fs.existsSync(PYTHON) ? PYTHON : "python",
    ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
    { cwd: BACKEND, windowsHide: true, stdio: "ignore" });
  backendProcess.on("error", e => dialog.showErrorBox("NOVA backend error", e.message));
  for (let i = 0; i < 40; i++) {
    if (await backendOnline()) return;
    await new Promise(r => setTimeout(r, 500));
  }
  throw new Error("Backend did not start. Check NOVA's Python venv and packages.");
}
function createWindow() {
  win = new BrowserWindow({
    width: 1280, height: 820, minWidth: 900, minHeight: 600,
    show: false, autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true, nodeIntegration: false
    }
  });
  win.once("ready-to-show", () => win.show());
  win.loadURL("http://127.0.0.1:5174");
  win.on("close", event => {
    if (!quitting) { event.preventDefault(); win.hide(); }
  });
}
function createTray() {
  tray = new Tray(path.join(__dirname, "nova-tray.png"));
  tray.setToolTip("NOVA Personal AI");
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Open NOVA", click: () => { win.show(); win.focus(); } },
    { type: "separator" },
    { label: "Quit NOVA", click: () => { quitting = true; app.quit(); } }
  ]));
  tray.on("double-click", () => { win.show(); win.focus(); });
}
app.whenReady().then(async () => {
  try { await startBackend(); createWindow(); createTray(); }
  catch (e) { dialog.showErrorBox("NOVA could not start", e.message); quitting = true; app.quit(); }
});
app.on("before-quit", () => {
  quitting = true;
  if (backendProcess && !backendProcess.killed) backendProcess.kill();
});
app.on("window-all-closed", () => { /* stay in tray */ });
