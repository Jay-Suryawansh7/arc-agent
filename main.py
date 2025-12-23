#!/usr/bin/env python3
"""
ARC - Autonomous Reasoning Companion
Main entry point with multiple modes
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional
import platform

# Windows-specific: Enable UTF-8 for console output to support emojis
if platform.system() == 'Windows':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

__version__ = "0.1.0"

# ASCII Art Banner
BANNER = """
╔═══════════════════════════════════════════════╗
║                                               ║
║    █████╗ ██████╗  ██████╗                   ║
║   ██╔══██╗██╔══██╗██╔════╝                   ║
║   ███████║██████╔╝██║                        ║
║   ██╔══██║██╔══██╗██║                        ║
║   ██║  ██║██║  ██║╚██████╗                   ║
║   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝                   ║
║                                               ║
║   Autonomous Reasoning Companion v{version}   ║
║                                               ║
╚═══════════════════════════════════════════════╝
"""

def setup_logging(debug: bool = False):
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('arc.log'),
            logging.StreamHandler()
        ]
    )

async def setup_wizard():
    """Interactive setup wizard."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    
    console = Console()
    
    console.print(Panel(
        "[bold cyan]ARC Setup Wizard[/bold cyan]\n"
        "Let's configure your assistant",
        border_style="cyan"
    ))
    
    # Check dependencies
    console.print("\n[bold]Checking dependencies...[/bold]")
    
    deps_ok = True
    try:
        import whisper
        console.print("✓ Whisper (STT) installed")
    except ImportError:
        console.print("✗ Whisper not installed - Run: pip install openai-whisper")
        deps_ok = False
    
    try:
        import pyaudio
        console.print("✓ PyAudio installed")
    except ImportError:
        console.print("✗ PyAudio not installed")
        deps_ok = False
    
    try:
        from langchain_ollama import ChatOllama
        console.print("✓ Ollama integration installed")
    except ImportError:
        console.print("✗ Ollama not installed - Run: pip install langchain-ollama")
        deps_ok = False
    
    if not deps_ok:
        console.print("\n[red]Please install missing dependencies first[/red]")
        return
    
    # Configure LLM
    console.print("\n[bold]LLM Configuration[/bold]")
    backend = Prompt.ask(
        "Choose LLM backend",
        choices=["ollama", "openai", "llamacpp"],
        default="ollama"
    )
    
    if backend == "ollama":
        model = Prompt.ask("Ollama model name", default="gemma3:4b")
        base_url = Prompt.ask("Ollama URL", default="http://localhost:11434")
        
        config_lines = [
            "# LLM Configuration",
            "LLM__BACKEND=ollama",
            f"LLM__BASE_URL={base_url}",
            f"LLM__MODEL_NAME={model}",
            "LLM__TEMPERATURE=0.7",
            "LLM__CONTEXT_SIZE=4096",
        ]
    
    # Voice configuration
    console.print("\n[bold]Voice Configuration[/bold]")
    stt_model = Prompt.ask(
        "Whisper model size",
        choices=["tiny", "base", "small", "medium"],
        default="base"
    )
    
    config_lines.extend([
        "",
        "# Voice Configuration",
        "VOICE__WAKE_WORD=arc",
        f"VOICE__STT_MODEL_SIZE={stt_model}",
        "VOICE__TTS_VOICE=models/piper/en_US-lessac-medium.onnx",
        "",
        "# System",
        "SYSTEM__DEBUG=false"
    ])
    
    # Write .env
    env_path = Path(".env")
    with open(env_path, 'w') as f:
        f.write('\n'.join(config_lines))
    
    console.print(f"\n[green]✓ Configuration saved to {env_path}[/green]")
    
    # Test LLM
    if Confirm.ask("\nTest LLM connection?"):
        await test_llm()

async def test_llm():
    """Test LLM connection."""
    from rich.console import Console
    console = Console()
    
    try:
        from arc.config import get_config
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        config = get_config()
        console.print(f"Testing {config.llm.model_name}...")
        
        llm = ChatOllama(
            model=config.llm.model_name,
            base_url=config.llm.base_url
        )
        
        response = llm.invoke([HumanMessage(content="Say hello")])
        console.print(f"[green]✓ LLM Response: {response.content}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ LLM Test Failed: {e}[/red]")

async def test_components():
    """Test all components."""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    table = Table(title="Component Tests")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Message")
    
    # Test LLM
    try:
        from arc.config import get_config
        from langchain_ollama import ChatOllama
        config = get_config()
        llm = ChatOllama(model=config.llm.model_name, base_url=config.llm.base_url)
        llm.invoke([{"role": "user", "content": "test"}])
        table.add_row("LLM", "[green]✓[/green]", f"{config.llm.model_name}")
    except Exception as e:
        table.add_row("LLM", "[red]✗[/red]", str(e)[:50])
    
    # Test STT
    try:
        from arc.voice.stt import get_whisper_stt
        stt = get_whisper_stt()
        table.add_row("STT", "[green]✓[/green]", "Whisper ready")
    except Exception as e:
        table.add_row("STT", "[red]✗[/red]", str(e)[:50])
    
    # Test TTS
    try:
        from arc.voice.tts import get_piper_tts
        tts = get_piper_tts()
        table.add_row("TTS", "[green]✓[/green]", "Piper ready")
    except Exception as e:
        table.add_row("TTS", "[red]✗[/red]", str(e)[:50])
    
    # Test Tools
    try:
        from arc.tools.system_tools import list_running_apps
        apps = list_running_apps.invoke({})
        table.add_row("System Tools", "[green]✓[/green]", f"{len(apps)} apps")
    except Exception as e:
        table.add_row("System Tools", "[red]✗[/red]", str(e)[:50])
    
    console.print(table)

async def run_cli_mode():
    """Run CLI mode."""
    from cli import main as cli_main
    await cli_main()

async def run_voice_mode():
    """Run voice mode."""
    from arc.voice.loop import start_voice_loop
    from cli import agent_callback
    await start_voice_loop(agent_callback)

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ARC - Autonomous Reasoning Companion",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--mode',
        choices=['cli', 'voice', 'tray', 'daemon'],
        default='cli',
        help='Operating mode (default: cli)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to config file'
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Run setup wizard'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test all components'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'ARC v{__version__}'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    
    # Show banner
    print(BANNER.format(version=__version__))
    
    try:
        # Setup wizard
        if args.setup:
            await setup_wizard()
            return
        
        # Test components
        if args.test:
            await test_components()
            return
        
        # Check if config exists
        if not Path('.env').exists() and not args.setup:
            print("\n⚠️  No configuration found. Run 'python main.py --setup' first.\n")
            return
        
        # Run selected mode
        logger.info(f"Starting ARC in {args.mode} mode...")
        
        if args.mode == 'cli':
            await run_cli_mode()
        
        elif args.mode == 'voice':
            await run_voice_mode()
        
        elif args.mode == 'tray':
            print("System tray mode not implemented yet")
        
        elif args.mode == 'daemon':
            print("Daemon mode not implemented yet")
        
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("Run with --debug for more details")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
