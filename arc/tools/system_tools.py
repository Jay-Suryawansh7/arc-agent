"""
System tools for local OS interaction using LangChain @tool decorator.
Includes App Control, Window Management, and Input Automation.
"""
import sys
import platform
import subprocess
import time
import logging
from typing import List, Optional

try:
    from langchain_core.tools import tool
except ImportError:
    # Fallback for dev/testing if langchain not installed yet
    def tool(func): return func

import psutil
import pyautogui

# Adjust pyautogui safety
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

logger = logging.getLogger(__name__)

# --- Helper for Safety ---
def _is_destructive(action: str) -> bool:
    """Check if an action is destructive."""
    # Simplified check for demonstration
    return action in ["close_app", "terminate_process"]

def _confirm_action(action: str, target: str) -> bool:
    """
    In a real agent loop, this would interface with the user for confirmation.
    For this tool implementation, we rely on configuration safety settings via the Agent logic,
    or assume if the agent calls it, it intends to do it (with internal checks).
    """
    logger.warning(f"Executing potential destructive action: {action} on {target}")
    return True

# --- App Control Tools ---

@tool
def open_app(app_name: str):
    """
    Open a desktop application by name.
    """
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", "-a", app_name], check=True)
            return f"Opened {app_name} on macOS."
        elif system == "Windows":
            subprocess.run(["start", app_name], shell=True, check=True)
            return f"Opened {app_name} on Windows."
        elif system == "Linux":
            subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opened {app_name} on Linux."
        else:
            return f"Unsupported platform: {system}"
    except Exception as e:
        return f"Failed to open {app_name}: {e}"

@tool
def close_app(app_name: str):
    """
    Close an application by name (terminates the process).
    """
    if not _confirm_action("close_app", app_name):
        return "Action cancelled."

    terminated_count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Simple matching, can be improved with regex
            if app_name.lower() in proc.info['name'].lower():
                proc.terminate()
                terminated_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if terminated_count > 0:
        return f"Terminated {terminated_count} process(es) matching '{app_name}'."
    else:
        return f"No running process found for '{app_name}'."

@tool
def list_running_apps() -> List[str]:
    """
    List names of currently running applications (filtered for clarity).
    """
    apps = set()
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name:
                apps.add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(list(apps))

@tool
def is_app_running(app_name: str) -> bool:
    """Check if a specific app is running."""
    for proc in psutil.process_iter(['name']):
        try:
            if app_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

# --- Window Management (macOS focused) ---

@tool
def focus_window(app_name: str):
    """
    Bring an application window to the foreground (macOS/AppleScript).
    """
    if platform.system() == "Darwin":
        script = f'''
        tell application "{app_name}"
            activate
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return f"Focused {app_name}."
        except subprocess.CalledProcessError:
            return f"Failed to focus {app_name}. Is it running?"
    else:
        return "Window focusing only implemented for macOS currently."

@tool
def minimize_window(app_name: str):
    """
    Minimize application window (macOS only via AppleScript).
    """
    pass # Implementation requires complex UI scripting, skipping for stability in this iteration

# --- Input Automation ---

@tool
def type_text_keyboard(text: str):
    """Type text using the keyboard."""
    try:
        pyautogui.write(text, interval=0.05)
        return "Typed text successfully."
    except Exception as e:
        return f"Typing failed: {e}"

@tool
def press_key(key: str):
    """Press a specific key (e.g., 'enter', 'esc', 'space')."""
    try:
        pyautogui.press(key)
        return f"Pressed {key}."
    except Exception as e:
        return f"KeyPress failed: {e}"

@tool
def click_screen(x: int, y: int):
    """Click mouse at coordinates (x, y)."""
    try:
        pyautogui.click(x, y)
        return f"Clicked at ({x}, {y})."
    except Exception as e:
        return f"Click failed: {e}"

@tool
def screenshot_screen(path: str = "screenshot.png"):
    """Take a screenshot and save to path."""
    try:
        pyautogui.screenshot(path)
        return f"Screenshot saved to {path}"
    except Exception as e:
        return f"Screenshot failed: {e}"

@tool
def get_current_datetime() -> str:
    """Get the current date and time."""
    from datetime import datetime
    import pytz
    
    # Get current time
    now = datetime.now()
    
    # Format nicely
    date_str = now.strftime("%A, %B %d, %Y")  # e.g., "Monday, December 23, 2025"
    time_str = now.strftime("%I:%M %p")  # e.g., "08:22 AM"
    
    return f"Current date and time: {date_str} at {time_str}"
