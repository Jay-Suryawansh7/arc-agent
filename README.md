# ARC - Autonomous Reasoning Companion 🤖

> **A local, voice-controlled AI assistant for macOS, Linux, and Windows.**

ARC is a Jarvis-like assistant that lives on your machine. It can control your system, manage apps, browse the web, and remember your conversations—all while running locally for maximum privacy.

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-purple)

## ✨ Features

- **🗣️ Unified Voice Loop**: Seamless speech-to-text (Whisper) and text-to-speech (Piper) with interrupt handling.
- **🖥️ System Control**: Open apps, take screenshots, check running processes, and manage windows.
- **🌐 Web Automation**: Open generic websites or specific "hybrid" web apps like WhatsApp and Spotify.
- **🧠 Local Intelligence**: Powered by **Ollama** (Gemma, Llama 3, Mistral) for privacy-first reasoning.
- **💾 Persistent Memory**: Encrypted database to remember user details across sessions.
- **💻 CLI & Voice Modes**: Interact via text terminal or hands-free voice commands.

---

## 🚀 Prerequisites

### 1. Install Ollama
ARC uses [Ollama](https://ollama.com/) for its brain. 
- **Download**: [https://ollama.com/download](https://ollama.com/download)
- **Pull a model**:
  ```bash
  ollama pull gemma2:2b    # Recommended for speed
  # OR
  ollama pull llama3       # For better reasoning
  ```

### 2. System Dependencies
ARC handles audio input/output, so you need system audio libraries.

#### 🍎 macOS
```bash
brew install portaudio
```

#### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3-pyaudio portaudio19-dev espeak-ng
```

#### 🪟 Windows
1. Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (required for PyAudio).
2. Ensure you have Python installed from python.org.

---

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Jay-Suryawansh7/arc-agent.git
   cd arc-agent
   ```

2. **Create a virtual environment** (Recommended):
   ```bash
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(If `requirements.txt` is missing, run: `pip install langchain-ollama openai-whisper piper-tts pyaudio psutil pyautogui rich cryptography pydantic-settings`)*

---

## ⚡ Quick Start

### 1. Run Setup Wizard
Initialize your configuration and check dependencies:
```bash
python main.py --setup
```

### 2. Output Modes

**🎤 Voice Mode (The Real Experience)**
Hands-free interaction.
```bash
python main.py --mode voice
```

**⌨️ CLI Mode (Text Chat)**
Chat via terminal with rich formatting.
```bash
python main.py --mode cli
```

---

## 🗣️ Voice Commands

ARC understands natural language, but here are some specific triggers:

| Category | Command Examples | Action |
|----------|------------------|--------|
| **Apps** | "Open **Calculator**" | Opens the system app. |
| | "Launch **Visual Studio Code**" | smart app launching. |
| **Web** | "Open **WhatsApp** on browser" | Opens web.whatsapp.com |
| | "Visit **GitHub**" | Opens github.com |
| **System** | "Take a **screenshot**" | Saves screen capture. |
| | "List running apps" | Shows active processes. |
| | "What time is it?" | Shows real-time clock. |
| **General** | "Project list" | (If configured) Shows git projects. |

---

## 🧩 Hybrid App Handling

ARC is smart about "Hybrid" apps that exist as both Desktop Apps and Websites (like WhatsApp, Spotify, Slack).

- **"Open WhatsApp"** → Opens the **Desktop App** (Default).
- **"Open WhatsApp on browser"** → Opens the **Web Version**.

---

## 🐛 Troubleshooting

**Voice not detected?**
- Check your microphone settings in OS.
- Run `python test_mic.py` (if available) to verify input.

**"PortAudio" error during install?**
- Make sure you installed the system dependencies listed in prerequisites.

**LLM not responding?**
- Ensure Ollama is running (`ollama serve` or app is open).
- Check model name in `.env` matches what you pulled.

---

## 🤝 Contributing

1. Fork the repo.
2. Create a feature branch.
3. Commit your changes.
4. Push to the branch.
5. Create a Pull Request.

---

**License**: MIT
