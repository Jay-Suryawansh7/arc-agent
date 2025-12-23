"""
CLI Interface for ARC - Text-based interaction with rich formatting.
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.progress import Progress
    from rich.prompt import Prompt
    from rich import print as rprint
except ImportError:
    print("rich library not installed. Run: pip install rich")
    sys.exit(1)

console = Console()

class ARCCLIInterface:
    """Interactive CLI for ARC with rich formatting."""
    
    def __init__(self, agent_callback: Callable):
        """
        Initialize CLI.
        
        Args:
            agent_callback: Async function to process commands
        """
        self.agent_callback = agent_callback
        self.conversation_history = []
        self.running = False
        self.session_file = Path.home() / ".arc_session.json"
        
    def show_welcome(self):
        """Display welcome message."""
        welcome = Panel(
            "[bold cyan]ARC - Autonomous Reasoning Companion[/bold cyan]\n"
            "[dim]Text-based interface. Type /help for commands.[/dim]",
            title="🤖 Welcome",
            border_style="cyan"
        )
        console.print(welcome)
    
    def show_help(self):
        """Display help information."""
        table = Table(title="Available Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        
        table.add_row("/help", "Show this help message")
        table.add_row("/status", "Show system status")
        table.add_row("/clear", "Clear conversation history")
        table.add_row("/save [file]", "Save conversation")
        table.add_row("/load [file]", "Load conversation")
        table.add_row("/tools", "List available tools")
        table.add_row("/exit or /quit", "Exit ARC")
        
        console.print(table)
    
    def show_status(self):
        """Display system status."""
        from arc.config import get_config
        config = get_config()
        
        table = Table(title="System Status", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status")
        
        table.add_row("LLM Backend", f"{config.llm.backend} ({config.llm.model_name})")
        table.add_row("Voice STT", config.voice.stt_model_size)
        table.add_row("Voice TTS", "Piper")
        table.add_row("Conversation History", f"{len(self.conversation_history)} messages")
        
        console.print(table)
    
    def show_tools(self):
        """Display available tools."""
        from arc.tools.system_tools import (
            open_app, close_app, list_running_apps,
            screenshot_screen
        )
        
        table = Table(title="Available Tools", show_header=True)
        table.add_column("Tool", style="cyan")
        table.add_column("Description")
        
        table.add_row("open_app", "Open desktop applications")
        table.add_row("close_app", "Close applications")
        table.add_row("list_running_apps", "List running processes")
        table.add_row("screenshot", "Capture screen")
        table.add_row("type_text", "Simulate keyboard input")
        
        console.print(table)
    
    def save_conversation(self, filename: Optional[str] = None):
        """Save conversation to file."""
        if not filename:
            filename = f"arc_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = Path(filename)
        with open(filepath, 'w') as f:
            json.dump(self.conversation_history, f, indent=2, default=str)
        
        console.print(f"[green]✓[/green] Saved to {filepath}")
    
    def load_conversation(self, filename: str):
        """Load conversation from file."""
        filepath = Path(filename)
        if not filepath.exists():
            console.print(f"[red]✗[/red] File not found: {filepath}")
            return
        
        with open(filepath, 'r') as f:
            self.conversation_history = json.load(f)
        
        console.print(f"[green]✓[/green] Loaded {len(self.conversation_history)} messages")
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        console.print("[green]✓[/green] Conversation history cleared")
    
    async def process_command(self, user_input: str):
        """Process user command or message."""
        # Handle CLI commands
        if user_input.startswith('/'):
            parts = user_input[1:].split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            if cmd == 'help':
                self.show_help()
            elif cmd == 'status':
                self.show_status()
            elif cmd == 'tools':
                self.show_tools()
            elif cmd == 'clear':
                self.clear_history()
            elif cmd == 'save':
                self.save_conversation(args[0] if args else None)
            elif cmd == 'load':
                if args:
                    self.load_conversation(args[0])
                else:
                    console.print("[red]✗[/red] Usage: /load <filename>")
            elif cmd in ['exit', 'quit']:
                self.running = False
            else:
                console.print(f"[red]✗[/red] Unknown command: /{cmd}")
            
            return
        
        # Add to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now()
        })
        
        # Process with agent
        console.print("[dim]Processing...[/dim]")
        
        try:
            response = await self.agent_callback(user_input)
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now()
            })
            
            # Display response
            response_panel = Panel(
                response,
                title="[bold green]ARC[/bold green]",
                border_style="green"
            )
            console.print(response_panel)
            
        except Exception as e:
            console.print(f"[red]✗ Error:[/red] {str(e)}")
    
    async def start(self):
        """Start the CLI interface."""
        self.running = True
        self.show_welcome()
        
        console.print("\n[dim]Type your message or /help for commands[/dim]\n")
        
        while self.running:
            try:
                # Get user input
                user_input = await asyncio.to_thread(
                    Prompt.ask,
                    "[bold cyan]You[/bold cyan]"
                )
                
                if not user_input.strip():
                    continue
                
                await self.process_command(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
                continue
            except EOFError:
                break
        
        console.print("\n[cyan]👋 Goodbye![/cyan]")

async def start_cli(agent_callback: Callable):
    """
    Start the CLI interface.
    
    Args:
        agent_callback: Async function to process commands
    """
    cli = ARCCLIInterface(agent_callback)
    await cli.start()
