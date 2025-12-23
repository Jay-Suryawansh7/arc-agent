# ARC - Autonomous Reasoning Companion

ARC is a Jarvis-like AI assistant designed for autonomy and seamless integration with your digital environment. It combines voice control, MCP (Model Context Protocol) integration, and powerful system tools to act as a true companion.

## Key Features

- **Voice Control**: Wake word detection (Porcupine), Speech-to-Text (Whisper), and Text-to-Speech (Piper).
- **MCP Integration**: Connects to Model Context Protocol servers for extended capabilities.
- **Browser Control**: deep integration with web browsers for automation.
- **Git & GitHub**: Manage repositories and handle version control tasks.
- **System Control**: Execute Python code, manage files, and interact with the OS.
- **Communication**: Send emails and interact with messaging platforms (WhatsApp).

## Architecture

ARC is built on a modular architecture:
- **Core**: Handles LLM inference (Llama.cpp), decision making (DeepAgent), and memory.
- **MCP**: Manages connections to external tools and data contexts.
- **Tools**: Native system tools and integrations.
- **Voice**: Handles the audio input/output loop.
- **UI**: Provides CLI and Tray interfaces for interaction.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/arc-assistant.git
    cd arc-assistant
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install .
    ```

    *Note: `llama-cpp-python` may require specific build flags depending on your hardware (Metal for Mac, CUDA for NVIDIA).*

3.  **Configuration:**
    Copy `.env.example` to `.env` and fill in your credentials.
    ```bash
    cp .env.example .env
    ```

## Quick Start

Run the main application:

```bash
python main.py
```

This will start the voice loop and the system tray icon (if enabled). You can also run with specific flags (check `python main.py --help` for options).
