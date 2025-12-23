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

# Agent Callback
from arc.brain.graph import create_graph

# Initialize graph once
agent_graph = create_graph()

async def agent_callback(text_input: str) -> dict:
    """
    Callback for voice loop to process input using LangGraph.
    Returns: {"text": str, "tone": str}
    """
    try:
        # Run graph
        initial_state = {
            "input_text": text_input,
            "chat_history": [] # TODO: maintain history
        }
        
        # Invoke graph (synchronous execution for now due to LangGraph async traits/event loop)
        import asyncio
        result = await asyncio.to_thread(agent_graph.invoke, initial_state)
        
        intent = result.get("intent")
        tone = "friendly"
        
        # Determine Tone
        if result.get("recovery_attempt"):
            tone = "apologetic"
        elif intent == "tool":
            tone = "neutral"
            
        # Determine Text
        response_text = ""
        
        # Check recovery first
        if result.get("recovery_attempt"):
            response_text = result.get('final_response', "I'm sorry, something went wrong.")

        elif intent == "chat":
            response_text = result.get('final_response', "I'm not sure what to say.")
            
        elif intent == "tool":
            tool_res = result.get("tool_result", "")
            final_res = result.get("final_response", "Done.")
            
            # If tool result is an error but recovery didn't trigger, handle gracefully
            if "error" in str(tool_res).lower() and not result.get("recovery_attempt"):
                 tone = "apologetic"
                 response_text = f"{final_res} (Tool result: {tool_res})"
            else:
                 response_text = f"{final_res} Result: {tool_res}"
            
        else:
            tone = "apologetic"
            response_text = "I didn't understand that request."
            
        return {"text": response_text, "tone": tone}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"text": f"System error: {e}", "tone": "apologetic"}

async def main():
    """Main entry point for CLI mode"""
    await start_cli(agent_callback)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
