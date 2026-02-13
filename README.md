# 🤖 Jarvis AI Assistant — Mark XVIII

A powerful, local AI desktop assistant powered by **DeepSeek AI**, inspired by Jarvis from Iron Man. Built in Python with voice control, system automation, and deep intelligence.

## ⚡ Features

| Category | Capabilities |
|----------|-------------|
| 🧠 **AI Brain** | **OpenRouter** (Llama 3/4 Free) — reasoning, coding, general intelligence |
| 🎙️ **Voice** | Offline speech recognition (Vosk) + Edge TTS (natural voice) |
| 💻 **System Control** | Open apps, file operations, clipboard, volume, screenshots |
| 🔍 **Web Search** | SerpAPI or browser fallback for Google searches |
| 🌤️ **Weather** | Free weather reports via wttr.in (no API key needed) |
| 💬 **Messaging** | Send WhatsApp messages via desktop automation |
| 🧮 **Calculator** | Math expressions with safe evaluation |
| 📝 **Notes** | Save and retrieve notes persistently |
| ⏰ **Timer** | Set countdown timers with alerts |
| 🔒 **PC Control** | Shutdown, restart, sleep, lock |
| 🧠 **Memory** | Remembers your name, preferences, and relationships |
| 🎨 **GUI** | Animated Jarvis face with speaking visualization |

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** — [Download Python](https://www.python.org/downloads/)
- **Microphone** — Any USB or built-in microphone

### 2. Install Dependencies
```bash
cd c:\Users\ansh1\Desktop\temp\assists
pip install -r requirements.txt
```

### 3. Download Voice Model (Vosk)
Download the English model from [Vosk Models](https://alphacephei.com/vosk/models):
- Get: **vosk-model-small-en-us-0.15** (40MB)
- Extract the folder into this project directory

### 4. Get OpenRouter API Key (FREE!)
1. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
2. Sign up (Google/GitHub)
3. Generate a free key
4. The app will ask for it when you launch — or set it in `.env`

### 5. Launch Jarvis
```bash
python main.py
```

## 🎯 How to Use

### Voice Commands (just say them!)
| Command | What Happens |
|---------|-------------|
| "Open Chrome" | Launches Google Chrome |
| "What's the weather in Mumbai?" | Gets weather report |
| "Take a screenshot" | Saves screenshot to Pictures |
| "What's my CPU usage?" | Shows system stats |
| "Search for AI news" | Searches the web |
| "Send a message to John on WhatsApp" | Sends WhatsApp message |
| "Set a timer for 5 minutes" | Starts countdown timer |
| "Calculate 234 times 567" | Does math |
| "Remember my name is Ansh" | Saves to memory |
| "Take a note: buy groceries" | Saves a note |
| "Volume up" / "Mute" | Controls volume |
| "Lock the PC" | Locks workstation |
| "Stop" / "Mute" | Interrupts Jarvis |

### Chat Naturally
Just talk to Jarvis like a person — ask questions, have conversations, get help.

## 📁 Project Structure

```
assists/
├── main.py                  # Entry point
├── config.py                # Configuration
├── ui.py                    # GUI with animated face
├── requirements.txt         # Dependencies
├── .env.template            # API key template
├── core/
│   ├── llm.py               # DeepSeek AI engine
│   ├── speech_to_text.py    # Voice recognition (Vosk)
│   ├── tts.py               # Text-to-speech (Edge TTS)
│   └── prompt.txt           # System prompt (15 intents)
├── actions/
│   ├── open_app.py          # App launcher
│   ├── web_search.py        # Web search
│   ├── weather_report.py    # Weather info
│   ├── send_message.py      # WhatsApp messages
│   └── system_control.py    # System actions (10 handlers)
├── memory/
│   ├── memory_manager.py    # Long-term memory
│   └── temporary_memory.py  # Session memory
├── config/                  # API keys (auto-created)
├── assets/                  # Face image, icons
└── logs/                    # Runtime logs
```

## 🔐 Security

- Runs **100% locally** on your PC
- API calls only to DeepSeek for intelligence
- Dangerous operations (delete, shutdown) require confirmation
- Protected system directories cannot be modified
- Token usage tracked to stay within free tier

## 🎨 Customization

Edit `.env` or `config.py` to change:
- **TTS Voice** — Choose from 100+ Microsoft Edge voices
- **Wake word** — Change from "Hey Jarvis" to anything
- **AI Model** — Switch between `deepseek-chat` and `deepseek-reasoner`
- **Hotkey** — Default is `Ctrl+Shift+J`

## ⚠️ Troubleshooting

| Issue | Fix |
|-------|-----|
| "Vosk model not found" | Download & extract model to project folder |
| "API key not found" | Enter key in the setup UI or add to config/api_keys.json |
| "No microphone" | Check microphone is connected and not in use |
| "Edge TTS error" | Check internet connection (TTS needs internet) |

---

Built with ❤️ using DeepSeek AI + Python
