import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.config import get_config

try:
    config = get_config()
    print("Configuration loaded successfully!")
    print(f"Project Root: {config.system.project_root}")
    print(f"Models Dir: {config.system.models_dir}")
    print(f"Wake Word: {config.voice.wake_word}")
    print(f"Debug Mode: {config.system.debug}")
    print("Verification passed.")
except Exception as e:
    print(f"Configuration failed to load: {e}")
    sys.exit(1)
