import threading
from collections import deque
import sys
import datetime

# Global log buffer
log_buffer = deque(maxlen=100)
log_lock = threading.Lock()

# Global bot instance
bot = None
# Global execution control
is_running = False
current_thread = None

# Discord Globals
discord_client = None
discord_tree = None
discord_loop = None
discord_thread = None

# Threading Events for Wait Nodes: {node_id: threading.Event}
wait_events = {}

# Command Hooks: {command_name: callback_function}
# Global registry for what logic to run when a named command is triggered.
command_hooks = {}


def log_message(message):
    """Log message to global buffer and stdout"""
    # Print to real stdout for server logs
    sys.__stdout__.write(f"{message}\n")
    sys.__stdout__.flush()
    
    with log_lock:
        # Use UTC timestamp for consistency, client converts to local
        ts = datetime.datetime.utcnow().isoformat() + 'Z'
        log_buffer.append({"timestamp": ts, "message": message})
        
        # Write to file
        try:
            with open("server.log", "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {message}\n")
        except Exception:
            pass
