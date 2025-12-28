import shared
from shared import log_message
from bluestacks_bot import BlueStacksBot
from context import RuntimeContext
from executor import GraphExecutor

def start_adb_server():
    """Start local ADB server if not running"""
    import subprocess
    import os
    try:
        log_message("Checking/Starting ADB Server...")
        subprocess.run(["adb", "start-server"], check=True)
    except FileNotFoundError:
        bs_adb = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
        if os.path.exists(bs_adb):
            log_message(f"Standard 'adb' not found. Using BlueStacks ADB: {bs_adb}")
            subprocess.run([bs_adb, "start-server"], check=True)
        else:
            log_message("Failed to find 'adb' or 'HD-Adb.exe'. Please install ADB or add it to PATH.")
            raise
    except Exception as e:
        log_message(f"Failed to start ADB server: {e}")

def get_bot(bot_instance=None):
    if bot_instance is None:
        start_adb_server()
        import os
        from settings import load_settings
        
        settings = load_settings()
        
        # Priority: Environment Variable > settings.json > Default
        default_host = "host.docker.internal" if os.environ.get("ADB_HOST") == "host.docker.internal" else "127.0.0.1"
        device_host = os.environ.get("ADB_HOST") or settings.get("adb_host") or default_host
        device_port = int(os.environ.get("ADB_PORT") or settings.get("adb_port") or 5555)
        
        log_message(f"Connecting to ADB at {device_host}:{device_port}")
        bot_instance = BlueStacksBot(device_host=device_host, device_port=device_port, logger=log_message)
    return bot_instance

def execute_graph(nodes_list, recursion_depth=0, start_node_id=None):
    """
    Adapter function for backward compatibility.
    Creates a Context and runs the GraphExecutor.
    """
    try:
        # Get Bot
        from shared import bot
        bot_instance = get_bot(bot)
        shared.bot = bot_instance
        
        # Create Context
        # Note: If this is a recursive call from OLD code (unlikely now?), we might lose context.
        # But since we replaced the recursion in ScriptNode to use executor directly,
        # execute_graph is only called from the TOP LEVEL (routes/discord_manager).
        
        context = RuntimeContext(
            bot=bot_instance,
            is_running=shared.is_running,
            discord_client=shared.discord_client,
            discord_loop=shared.discord_loop,
            wait_events=shared.wait_events
        )
        context.recursion_depth = recursion_depth
        
        executor = GraphExecutor()
        success = executor.execute(nodes_list, context, start_node_id=start_node_id)
        return success

    except Exception as e:
        log_message(f"Execution Error: {e}")
        return False
