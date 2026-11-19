NOVA WINDOWS FEATURES UPDATE

1. Back up your NOVA folder.
2. Copy install_nova_features.py into the NOVA ROOT folder (same level as backend and frontend).
3. Open Git Bash in that folder and run:

   source venv/Scripts/activate
   python install_nova_features.py
   pip install winotify
   cd frontend
   npm install
   npm run dev:desktop

NOVA opens in an Electron desktop window. Closing the window hides it in the
Windows system tray. Right-click the tray icon to Open NOVA or Quit NOVA.
The backend remains running while NOVA stays in the tray, so reminders can
trigger while the window is hidden.

VOICE COMMANDS (use microphone, then press Send):
- NOVA, add a task to study Java
- Create task to finish my assignment
- NOVA, remind me to study Java at 7 PM
- Remind me to drink water in 30 minutes
- Remind me to call home tomorrow at 8 AM

The parser supports AM/PM clock times, tomorrow, and relative minutes/hours.

TEST NOTIFICATION:
Open http://127.0.0.1:8000/docs, find POST /notifications/test, click Try it
out, then Execute. Check Windows notification settings/Focus Assist if absent.

This is a development-mode tray app. Automatic launch at Windows sign-in and
a packaged installer are not configured. Keep backend/database/nova.db.
