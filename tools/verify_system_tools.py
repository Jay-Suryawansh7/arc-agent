import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.tools.system_tools import list_running_apps, open_app, type_text_keyboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_system_tools():
    logger.info("Verifying System Tools...")
    
    # 1. List Apps (non-intrusive)
    try:
        apps = list_running_apps.invoke({}) # Invoke as LangChain app if decorated
        # Or direct call if decorator fallback used
        if hasattr(list_running_apps, 'invoke'):
            apps = list_running_apps.invoke({})
        else:
            apps = list_running_apps()
            
        logger.info(f"Running apps count: {len(apps)}")
        logger.info(f"First 5 apps: {apps[:5]}")
    except Exception as e:
        logger.error(f"List Apps failed: {e}")

    # 2. Input Simulation (Dry run / log only ideally, but we can try typing nothing effectively)
    # We won't actually open apps or type in this automated test to avoid disturbing user
    logger.info("Skipping interactive open_app/type_text tests in automated verification.")

if __name__ == "__main__":
    verify_system_tools()
