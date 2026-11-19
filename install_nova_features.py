
from pathlib import Path
import json

root = Path.cwd()
backend = root / "backend"
frontend = root / "frontend"
if not (backend / "main.py").exists() or not (frontend / "package.json").exists():
    raise SystemExit("Run from the NOVA project root (the folder containing backend and frontend).")

# Backend: Windows toast notifications from the existing reminder checker.
p = backend / "main.py"
s = p.read_text(encoding="utf-8")
if "from winotify import Notification" not in s:
    s = s.replace(
        "from pydantic import BaseModel, Field",
        "from pydantic import BaseModel, Field\n\ntry:\n    from winotify import Notification\nexcept ImportError:\n    Notification = None"
    )
a = s.find("async def reminder_checker():")
b = s.find("\n\n# ==========================================\n# APPLICATION LIFESPAN", a)
if a < 0 or b < 0:
    raise SystemExit("Could not locate reminder_checker() in backend/main.py.")
checker = r'''async def reminder_checker():
    # Show each due reminder once per backend run.
    notified = set()
    while True:
        try:
            due = await asyncio.to_thread(get_due_reminders)
            for reminder in due:
                key = str(reminder.get("id") or f"{reminder.get('title', '')}|{reminder.get('remind_at', '')}")
                if key in notified:
                    continue
                notified.add(key)
                title = str(reminder.get("title", "You have a reminder"))
                print("\\nNOVA REMINDER:", title)
                if Notification is not None:
                    try:
                        toast = Notification(
                            app_id="NOVA Personal AI",
                            title="NOVA Reminder",
                            msg=title,
                            duration="long"
                        )
                        await asyncio.to_thread(toast.show)
                    except Exception as toast_error:
                        print("Windows notification error:", toast_error)
                else:
                    print("Install winotify to enable Windows notifications.")
        except Exception as error:
            print("Reminder error:", error)
        await asyncio.sleep(10)
'''
s = s[:a] + checker + s[b:]
if '@app.post("/notifications/test")' not in s:
    route = '''

@app.post("/notifications/test")
def test_notification():
    if Notification is None:
        raise HTTPException(status_code=503, detail="Install winotify to enable Windows notifications.")
    try:
        Notification(
            app_id="NOVA Personal AI",
            title="NOVA",
            msg="Windows notifications are working!",
            duration="short"
        ).show()
        return {"success": True, "message": "Test notification sent"}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

'''
    s = s.replace("# ==========================================\n# HOME ROUTE", route + "# ==========================================\n# HOME ROUTE", 1)
p.write_text(s, encoding="utf-8")

# Frontend: parse spoken task/reminder commands locally and call existing APIs.
p = frontend / "src/App.jsx"
s = p.read_text(encoding="utf-8")
if not p.exists():
    raise SystemExit("Missing frontend/src/App.jsx")
if "async function tryHandleVoiceCommand" not in s:
    fn = r'''
  // VOICE TASKS AND REMINDERS
  function parseVoiceReminderTime(command) {
    const now = new Date();
    const lower = command.toLowerCase();
    const relative = lower.match(/\bin\s+(\d+)\s+(minute|minutes|min|hour|hours)\b/);
    if (relative) {
      const result = new Date(now);
      const amount = Number(relative[1]);
      if (relative[2].startsWith("hour")) result.setHours(result.getHours() + amount);
      else result.setMinutes(result.getMinutes() + amount);
      return result;
    }
    const match = lower.match(/\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b/);
    if (!match) return null;
    let hour = Number(match[1]);
    const minute = Number(match[2] || 0);
    if (hour < 1 || hour > 12 || minute > 59) return null;
    if (match[3] === "pm" && hour !== 12) hour += 12;
    if (match[3] === "am" && hour === 12) hour = 0;
    const result = new Date(now);
    if (/\btomorrow\b/.test(lower)) result.setDate(result.getDate() + 1);
    result.setHours(hour, minute, 0, 0);
    if (!/\btomorrow\b/.test(lower) && result <= now) result.setDate(result.getDate() + 1);
    return result;
  }

  async function tryHandleVoiceCommand(command) {
    const text = command.trim();
    const task = text.match(/^(?:nova[, ]*)?(?:please\s+)?(?:add|create|make)\s+(?:a\s+)?task(?:\s+to|\s+for)?\s+(.+)$/i);
    if (task) {
      const title = task[1].trim();
      const response = await fetch(`${API}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, priority: "medium" }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not create task");
      setMessages((old) => [...old,
        { role: "user", content: text },
        { role: "assistant", content: `Done. I've added the task: ${title}.` }
      ]);
      await loadTasks();
      await loadPlanner();
      if (voiceEnabled) speakResponse(`Done. I've added the task: ${title}.`);
      return true;
    }

    const reminder = text.match(/^(?:nova[, ]*)?(?:please\s+)?remind\s+me\s+to\s+(.+)$/i);
    if (reminder) {
      const details = reminder[1];
      const remindAt = parseVoiceReminderTime(details);
      if (!remindAt) {
        throw new Error("Please include a time, e.g. 'remind me to study Java at 7 PM' or 'remind me to drink water in 30 minutes'.");
      }
      const title = details
        .replace(/\btomorrow\b/i, "")
        .replace(/\bin\s+\d+\s+(?:minute|minutes|min|hour|hours)\b/i, "")
        .replace(/\b(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)\b/i, "")
        .trim().replace(/\s+/g, " ");
      if (!title) throw new Error("Please say what I should remind you about.");
      const response = await fetch(`${API}/reminders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, remind_at: remindAt.toISOString() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not create reminder");
      setMessages((old) => [...old,
        { role: "user", content: text },
        { role: "assistant", content: `Reminder set: ${title}, for ${remindAt.toLocaleString()}.` }
      ]);
      await loadReminders();
      await loadPlanner();
      if (voiceEnabled) speakResponse(`Reminder set for ${title}.`);
      return true;
    }
    return false;
  }
'''
    anchor = "  // =================================\n  // AI CHAT\n  // ================================="
    if anchor not in s:
        raise SystemExit("Could not find AI CHAT anchor in App.jsx.")
    s = s.replace(anchor, fn + "\n" + anchor, 1)
    anchor = "    const userMessage = input.trim();"
    replacement = '''    const userMessage = input.trim();

    try {
      const handled = await tryHandleVoiceCommand(userMessage);
      if (handled) {
        setInput("");
        setError("");
        return;
      }
    } catch (commandError) {
      setError(commandError.message);
      setMessages((old) => [...old,
        { role: "user", content: userMessage },
        { role: "assistant", content: commandError.message }
      ]);
      setInput("");
      return;
    }
'''
    if anchor not in s:
        raise SystemExit("Could not find sendMessage input anchor.")
    s = s.replace(anchor, replacement, 1)
p.write_text(s, encoding="utf-8")

# Electron tray shell. Close button hides window; Quit exits and stops backend child.
electron = frontend / "electron"
electron.mkdir(parents=True, exist_ok=True)
(electron / "main.cjs").write_text(r'''const { app, BrowserWindow, Tray, Menu, dialog } = require("electron");
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
''', encoding="utf-8")
(electron / "preload.cjs").write_text(
    'const { contextBridge } = require("electron");\ncontextBridge.exposeInMainWorld("novaDesktop", { isDesktop: true });\n',
    encoding="utf-8"
)

package_path = frontend / "package.json"
pkg = json.loads(package_path.read_text(encoding="utf-8"))
pkg["main"] = "electron/main.cjs"
pkg.setdefault("scripts", {})
pkg["scripts"]["dev"] = "vite --port 5174"
pkg["scripts"]["desktop"] = "electron ."
pkg["scripts"]["dev:desktop"] = 'concurrently -k "vite --host 127.0.0.1 --port 5174 --strictPort" "wait-on http://127.0.0.1:5174 && electron ."'
pkg.setdefault("devDependencies", {})
pkg["devDependencies"].update({"electron": "^36.0.0", "concurrently": "^9.1.2", "wait-on": "^8.0.3"})
package_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")

print("NOVA update installed. Next install dependencies and run npm run dev:desktop.")
