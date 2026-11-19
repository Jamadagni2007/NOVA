import { useEffect, useRef, useState } from "react";

import {
  Brain,
  MessageSquare,
  CheckSquare,
  Bell,
  CalendarDays,
  Settings,
  Send,
  Mic,
  Plus,
  Trash2,
  Circle,
  Activity,
  Sparkles,
  Volume2,
  VolumeX,
} from "lucide-react";

import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [activePage, setActivePage] = useState("Chat");

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm NOVA, your personal AI assistant. How can I help you today?",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [sessionId] = useState(() => {
    let id = localStorage.getItem("nova_session");

    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("nova_session", id);
    }

    return id;
  });

  const [tasks, setTasks] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [planner, setPlanner] = useState(null);

  const [taskTitle, setTaskTitle] = useState("");
  const [reminderTitle, setReminderTitle] = useState("");
  const [reminderTime, setReminderTime] = useState("");

  const [error, setError] = useState("");

  // VOICE RECOGNITION
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);

  // NOVA SPEAKING VOICE
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  // =================================
  // LOAD TASKS
  // =================================

  async function loadTasks() {
    try {
      const response = await fetch(`${API}/tasks`);

      if (!response.ok) throw new Error("Could not load tasks");

      const data = await response.json();
      setTasks(data.tasks || []);
    } catch (err) {
      setError(err.message);
    }
  }

  // =================================
  // LOAD REMINDERS
  // =================================

  async function loadReminders() {
    try {
      const response = await fetch(`${API}/reminders`);

      if (!response.ok) throw new Error("Could not load reminders");

      const data = await response.json();
      setReminders(data.reminders || []);
    } catch (err) {
      setError(err.message);
    }
  }

  // =================================
  // LOAD DAILY PLANNER
  // =================================

  async function loadPlanner() {
    try {
      const response = await fetch(`${API}/planner/today`);

      if (!response.ok) throw new Error("Could not load planner");

      const data = await response.json();
      setPlanner(data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadTasks();
    loadReminders();
    loadPlanner();
  }, []);

  // Stop microphone and speech when this component is removed.
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // =================================
  // NOVA TEXT-TO-SPEECH
  // =================================

  function speakResponse(text) {
    if (!voiceEnabled || !("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    utterance.rate = 0.95;
    utterance.pitch = 1.05;
    utterance.volume = 1;

    const voices = window.speechSynthesis.getVoices();

    // Prefer a feminine-sounding English voice if one is installed.
    const preferredVoice = voices.find((voice) =>
      /female|zira|aria|jenny|samantha|susan|heera|veena/i.test(voice.name)
    ) || voices.find((voice) =>
      voice.lang?.toLowerCase().startsWith("en-in")
    ) || voices.find((voice) =>
      voice.lang?.toLowerCase().startsWith("en")
    );

    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    window.speechSynthesis.speak(utterance);
  }

  // =================================
  // NOVA VOICE RECOGNITION
  // =================================

  function startListening() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError(
        "Voice recognition is not supported by this browser. Please use Google Chrome."
      );
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
      setError("");
    };

    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript;

      if (transcript) {
        setInput((previous) =>
          `${previous} ${transcript}`.trim()
        );
      }
    };

    recognition.onerror = (event) => {
      const message =
        event.error === "not-allowed"
          ? "Microphone permission was denied. Allow microphone access in your browser."
          : `Voice recognition error: ${event.error}`;

      setError(message);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch (err) {
      setError("Could not start the microphone. Please try again.");
      setIsListening(false);
    }
  }


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

  // =================================
  // AI CHAT
  // =================================

  async function sendMessage(e) {
    e.preventDefault();

    if (!input.trim() || loading) return;

    const userMessage = input.trim();

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


    setMessages((previous) => [
      ...previous,
      { role: "user", content: userMessage },
    ]);

    setInput("");
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "AI request failed");
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.response,
        },
      ]);

      speakResponse(data.response);
    } catch (err) {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: `I'm having trouble connecting to my AI engine. ${err.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  // =================================
  // CREATE TASK
  // =================================

  async function addTask(e) {
    e.preventDefault();

    if (!taskTitle.trim()) return;

    try {
      const response = await fetch(`${API}/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: taskTitle,
          priority: "medium",
        }),
      });

      if (!response.ok) throw new Error("Task creation failed");

      setTaskTitle("");
      await loadTasks();
      await loadPlanner();
    } catch (err) {
      setError(err.message);
    }
  }

  // =================================
  // COMPLETE TASK
  // =================================

  async function completeTask(id) {
    try {
      const response = await fetch(`${API}/tasks/${id}/complete`, {
        method: "PUT",
      });

      if (!response.ok) throw new Error("Could not complete task");

      await loadTasks();
      await loadPlanner();
    } catch (err) {
      setError(err.message);
    }
  }

  // =================================
  // DELETE TASK
  // =================================

  async function removeTask(id) {
    try {
      const response = await fetch(`${API}/tasks/${id}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Could not delete task");

      await loadTasks();
      await loadPlanner();
    } catch (err) {
      setError(err.message);
    }
  }

  // =================================
  // CREATE REMINDER
  // =================================

  async function addReminder(e) {
    e.preventDefault();

    if (!reminderTitle.trim() || !reminderTime) return;

    try {
      const response = await fetch(`${API}/reminders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: reminderTitle,
          remind_at: new Date(reminderTime).toISOString(),
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Reminder creation failed");
      }

      setReminderTitle("");
      setReminderTime("");

      await loadReminders();
      await loadPlanner();
    } catch (err) {
      setError(err.message);
    }
  }

  // =================================
  // DELETE REMINDER
  // =================================

  async function removeReminder(id) {
    try {
      const response = await fetch(`${API}/reminders/${id}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Could not delete reminder");

      await loadReminders();
      await loadPlanner();
    } catch (err) {
      setError(err.message);
    }
  }

  // =================================
  // SIDEBAR
  // =================================

  const navigation = [
    { name: "Chat", icon: MessageSquare },
    { name: "Tasks", icon: CheckSquare },
    { name: "Reminders", icon: Bell },
    { name: "Planner", icon: CalendarDays },
  ];

  function renderContent() {
    switch (activePage) {
      case "Chat":
        return (
          <div className="chat-page">
            <div className="chat-heading">
              <div>
                <span className="eyebrow">PERSONAL AI ASSISTANT</span>
                <h1>Welcome back.</h1>
                <p>What would you like to accomplish today?</p>
              </div>

              <div className="nova-orb">
                <Brain size={35} />
              </div>
            </div>

            <div className="chat-messages">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`message ${message.role}`}
                >
                  <div className="message-avatar">
                    {message.role === "assistant" ? (
                      <Sparkles size={17} />
                    ) : (
                      "Y"
                    )}
                  </div>

                  <div className="message-content">
                    <span>
                      {message.role === "assistant" ? "NOVA" : "YOU"}
                    </span>

                    <p>{message.content}</p>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="loading-text">
                  NOVA is thinking...
                </div>
              )}
            </div>

            <form className="chat-input" onSubmit={sendMessage}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  isListening
                    ? "Listening... speak now"
                    : "Ask NOVA anything..."
                }
              />

              <button
                type="button"
                className="mic-button"
                onClick={() => setVoiceEnabled((enabled) => !enabled)}
                title={voiceEnabled ? "Turn NOVA voice off" : "Turn NOVA voice on"}
                aria-label={voiceEnabled ? "Turn voice off" : "Turn voice on"}
              >
                {voiceEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
              </button>

              <button
                type="button"
                className="mic-button"
                onClick={startListening}
                title={isListening ? "Stop listening" : "Speak to NOVA"}
                aria-label={isListening ? "Stop listening" : "Start voice input"}
                style={{
                  background: isListening ? "#e63946" : undefined,
                  color: isListening ? "#ffffff" : undefined,
                }}
              >
                <Mic size={20} />
              </button>

              <button type="submit" disabled={loading}>
                <Send size={19} />
              </button>
            </form>

            {isListening && (
              <p className="voice-status">NOVA is listening. Speak now...</p>
            )}
          </div>
        );

      case "Tasks":
        return (
          <div className="content-page">
            <h1>My Tasks</h1>
            <p className="subtitle">Organize your work and priorities.</p>

            <form className="add-form" onSubmit={addTask}>
              <input
                value={taskTitle}
                onChange={(e) => setTaskTitle(e.target.value)}
                placeholder="Enter a new task..."
              />

              <button type="submit">
                <Plus size={18} /> Add Task
              </button>
            </form>

            <div className="item-list">
              {tasks.map((task) => (
                <div className="item-card" key={task.id}>
                  <button
                    className="icon-button"
                    onClick={() => completeTask(task.id)}
                    title="Complete task"
                  >
                    <Circle size={20} />
                  </button>

                  <div className="item-info">
                    <h3 className={task.status === "completed" ? "completed" : ""}>
                      {task.title}
                    </h3>
                    <span>{task.priority} priority · {task.status}</span>
                  </div>

                  <button
                    className="delete-button"
                    onClick={() => removeTask(task.id)}
                    title="Delete task"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}

              {tasks.length === 0 && (
                <p className="empty-state">No tasks yet. Add your first task.</p>
              )}
            </div>
          </div>
        );

      case "Reminders":
        return (
          <div className="content-page">
            <h1>Reminders</h1>
            <p className="subtitle">Never forget an important moment.</p>

            <form className="add-form reminder-form" onSubmit={addReminder}>
              <input
                value={reminderTitle}
                onChange={(e) => setReminderTitle(e.target.value)}
                placeholder="Reminder title..."
              />

              <input
                type="datetime-local"
                value={reminderTime}
                onChange={(e) => setReminderTime(e.target.value)}
              />

              <button type="submit">
                <Plus size={18} /> Add
              </button>
            </form>

            <div className="item-list">
              {reminders.map((reminder) => (
                <div className="item-card" key={reminder.id}>
                  <Bell size={20} className="item-icon" />

                  <div className="item-info">
                    <h3>{reminder.title}</h3>
                    <span>{new Date(reminder.remind_at).toLocaleString()}</span>
                  </div>

                  <button
                    className="delete-button"
                    onClick={() => removeReminder(reminder.id)}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}

              {reminders.length === 0 && (
                <p className="empty-state">No reminders scheduled.</p>
              )}
            </div>
          </div>
        );

      case "Planner":
        return (
          <div className="content-page">
            <h1>Daily Planner</h1>
            <p className="subtitle">
              Your overview for {planner?.date || "today"}.
            </p>

            <div className="stats-grid">
              <div className="stat-card">
                <span>Total Tasks</span>
                <h2>{planner?.total_tasks ?? 0}</h2>
              </div>

              <div className="stat-card">
                <span>Pending</span>
                <h2>{planner?.pending_tasks?.length ?? 0}</h2>
              </div>

              <div className="stat-card">
                <span>Completed</span>
                <h2>{planner?.completed_tasks?.length ?? 0}</h2>
              </div>
            </div>

            <h2 className="section-title">Today's Pending Tasks</h2>

            {(planner?.pending_tasks || []).map((task) => (
              <div className="item-card" key={task.id}>
                <CheckSquare size={20} className="item-icon" />
                <div className="item-info">
                  <h3>{task.title}</h3>
                  <span>{task.status}</span>
                </div>
              </div>
            ))}

            <h2 className="section-title">Today's Completed Tasks</h2>

            {(planner?.completed_tasks || []).map((task) => (
              <div className="item-card" key={task.id}>
                <CheckSquare size={20} className="item-icon" />
                <div className="item-info">
                  <h3>{task.title}</h3>
                  <span>{task.status}</span>
                </div>
              </div>
            ))}

            <h2 className="section-title">Today's Reminders</h2>

            {(planner?.reminders || []).map((reminder) => (
              <div className="item-card" key={reminder.id}>
                <Bell size={20} className="item-icon" />
                <div className="item-info">
                  <h3>{reminder.title}</h3>
                  <span>{new Date(reminder.remind_at).toLocaleString()}</span>
                </div>
              </div>
            ))}

            {!planner && (
              <p className="empty-state">Loading your daily plan...</p>
            )}
          </div>
        );

      default:
        return <h1>{activePage}</h1>;
    }
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Brain size={25} />
          </div>

          <div>
            <h2>NOVA</h2>
            <span>PERSONAL AI</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav>
          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={`nav-item ${
                  activePage === item.name ? "active" : ""
                }`}
                onClick={() => setActivePage(item.name)}
              >
                <Icon size={19} />
                {item.name}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item">
            <Settings size={19} />
            Settings
          </button>

          <div className="system-status">
            <span className="online-dot"></span>
            <div>
              <strong>System Online</strong>
              <small>NOVA Core Active</small>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">NOVA / {activePage}</span>
          </div>

          <div className="topbar-right">
            <Activity size={17} />
            <span>Local AI Engine</span>
            <span className="online-dot"></span>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError("")}>Dismiss</button>
          </div>
        )}

        {renderContent()}
      </main>
    </div>
  );
}

export default App;
