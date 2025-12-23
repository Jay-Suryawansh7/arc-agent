#!/usr/bin/env python3
"""
ARC CLI Mode - Text-based interface
"""
import asyncio
import logging
import sys
import re

from arc.ui.cli import start_cli
from arc.config import get_config
from langchain_core.messages import SystemMessage, HumanMessage
from arc.tools.system_tools import (
    open_app, close_app, list_running_apps,
    screenshot_screen, is_app_running
)

# Setup logging
logging.basicConfig(
    level=logging.WARNING,  # Less verbose in CLI mode
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

class CommandRouter:
    """Route commands to tools or AI"""
    
    @staticmethod
    def detect_tool_command(text: str):
        """Detect if user wants to use a tool (voice-friendly)"""
        text_lower = text.lower().strip()
        
        # Remove common filler words for voice
        text_lower = text_lower.replace('please ', '').replace('can you ', '').replace('could you ', '')
        
        # Browser opening (websites) - check this FIRST
        browser_keywords = ['browser', 'web', 'website', 'online', 'site']
        site_keywords = {
            'gmail': 'https://gmail.com',
            'youtube': 'https://youtube.com',
            'github': 'https://github.com',
            'google': 'https://google.com',
            'facebook': 'https://facebook.com',
            'twitter': 'https://twitter.com',
            'openrouter': 'https://openrouter.ai',
            'claude': 'https://claude.ai',
            'chatgpt': 'https://chat.openai.com',
            'perplexity': 'https://perplexity.ai',
        }
        
        # Hybrid apps - default to app unless web keywords are used
        hybrid_apps = {
            'whatsapp': 'https://web.whatsapp.com',
            'spotify': 'https://open.spotify.com',
        }
        
        if 'open' in text_lower or 'go to' in text_lower or 'browse' in text_lower or 'visit' in text_lower:
            # Check for pure site keywords first (always URLs)
            for site, url in site_keywords.items():
                if site in text_lower:
                    return ('open_url', {'url': url})
            
            # Check for hybrid apps - ONLY if web/browser context is present
            if any(kw in text_lower for kw in browser_keywords):
                for site, url in hybrid_apps.items():
                    if site in text_lower:
                        return ('open_url', {'url': url})
            
            # Check for explicit URL
            import re
            url_match = re.search(r'https?://[^\s]+', text)
            if url_match:
                return ('open_url', {'url': url_match.group(0)})
            
            # Check if browser/website keywords mentioned - assume it's a website
            if any(kw in text_lower for kw in browser_keywords):
                # Extract the site name and try to construct URL
                words = text_lower.split()
                try:
                    target_idx = -1
                    for kw in ['open', 'visit', 'browse']:
                        if kw in words:
                            target_idx = words.index(kw)
                            break
                    
                    if target_idx == -1: target_idx = 0

                    # Get the next 1-3 words (website name)
                    site_words = []
                    for i in range(target_idx + 1, min(target_idx + 4, len(words))):
                        if words[i] not in browser_keywords and words[i] not in ['the', 'a', 'to', 'on', 'in']:
                            site_words.append(words[i])
                    
                    if site_words:
                        site_name = ''.join(site_words)
                        for tld in ['.com', '.ai', '.io', '.org', '.net']:
                            potential_url = f'https://{site_name}{tld}'
                            return ('open_url', {'url': potential_url, 'guess': True})
                except:
                    pass
        
        # App opening - Generic fallback for ANY app
        # This handles "Open [App Name]" for any system application
        if 'open' in text_lower or 'launch' in text_lower or 'start' in text_lower:
            patterns = [
                r'(?:open|launch|start)\s+(?:the\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
                r'(?:open|launch|start)\s+([a-zA-Z]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    app_name = match.group(1).strip()
                    app_name = ' '.join(word.capitalize() for word in app_name.split())
                    return ('open_app', {'app_name': app_name})

        # App listing - stricter check to avoid "WhatsApp" triggering it
        # Must have "list" OR "show" ... AND "app" or "process"
        # Avoid simple substring check for "what" if it's part of "whatsapp"
        if (any(word in text_lower.split() for word in ['list', 'show']) or 'what is running' in text_lower) and \
           any(word in text_lower for word in ['app', 'program', 'process', 'running']):
             if 'whatsapp' not in text_lower: # Explicit safe guard
                return ('list_apps', {})   
        
        # Screenshot
        if any(word in text_lower for word in ['screenshot', 'screen shot', 'capture', 'snap']):
            return ('screenshot', {})
        
        # Check if app is running
        if 'running' in text_lower and ('is' in text_lower or 'check' in text_lower):
            match = re.search(r'(?:is|check)\s+([a-zA-Z]+)\s+running', text_lower)
            if match:
                return ('is_running', {'app_name': match.group(1).capitalize()})
        
        # Get current time/date
        if any(word in text_lower for word in ['time', 'date', 'day', 'today', 'clock', 'calendar']):
            if any(word in text_lower for word in ['what', 'tell', 'show', 'current', 'today', 'now']):
                return ('get_datetime', {})
        
        return None

async def agent_callback(user_input: str) -> str:
    """Process user input and return response."""
    config = get_config()
    router = CommandRouter()
    
    # Try tool routing first
    tool_cmd = router.detect_tool_command(user_input)
    
    if tool_cmd:
        tool_name, params = tool_cmd
        
        try:
            if tool_name == 'list_apps':
                apps = list_running_apps.invoke({})
                return f"You have {len(apps)} apps running. Top 10:\n" + "\n".join(f"- {app}" for app in apps[:10])
            
            elif tool_name == 'open_url':
                import subprocess
                url = params['url']
                is_guess = params.get('guess', False)
                
                if is_guess:
                    # Try .com first, it's most common
                    response_msg = f"✓ Trying to open {url}"
                else:
                    response_msg = f"✓ Opened {url} in your default browser"
                
                subprocess.run(['open', url], check=True)
                return response_msg
            
            elif tool_name == 'open_app':
                result = open_app.invoke(params)
                return result
            
            elif tool_name == 'screenshot':
                result = screenshot_screen.invoke({'path': '/tmp/arc_screenshot.png'})
                return result
            
            elif tool_name == 'is_running':
                result = is_app_running.invoke(params)
                app = params['app_name']
                return f"✓ Yes, {app} is currently running" if result else f"✗ No, {app} is not running"
            
            elif tool_name == 'get_datetime':
                from arc.tools.system_tools import get_current_datetime
                result = get_current_datetime.invoke({})
                return result
            
            else:
                return "Tool not implemented yet"
                
        except Exception as e:
            return f"Error executing tool: {str(e)}"
    
    # Use AI for general queries
    try:
        from langchain_ollama import ChatOllama
        
        llm = ChatOllama(
            model=config.llm.model_name,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature
        )
        
        system_prompt = "You are ARC, a helpful assistant. Be concise and helpful."
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input)
        ]
        
        response = llm.invoke(messages)
        return response.content
        
    except Exception as e:
        return f"AI Error: {str(e)}\nMake sure Ollama is running."

async def main():
    """Main entry point for CLI mode"""
    await start_cli(agent_callback)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
