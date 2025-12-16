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
        default_host = "host.docker.internal" if os.environ.get("ADB_HOST") == "host.docker.internal" else "127.0.0.1"
        device_host = os.environ.get("ADB_HOST", default_host)
        device_port = int(os.environ.get("ADB_PORT", 5555))
        
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
            wait_events=shared.wait_events # Share global wait events for now
        )
        context.recursion_depth = recursion_depth
        
        # Setup Start Node Logic for Executor
        # Executor looks for 'start' node or uses first.
        # If start_node_id is provided, we might need to filter or reorder?
        # GraphExecutor doesn't explicitly support start_node_id argument in execute yet.
        # It finds 'start' type.
        # If start_node_id is passed, it implies starting from a SPECIFIC node (e.g. Slash Command trigger).
        # We need to handle this.
        
        # Quick fix: If start_node_id represents a 'start' type node, it's fine.
        # If it represents an arbitrary node, we need Executor to support starting from ID.
        
        # Let's modify nodes_list logic if start_node_id is provided?
        # A slash command trigger starts from a 'bot/discord_slash' node usually.
        # Engine.py previously did: current_node = node_map.get(start_node_id)
        
        # We should update GraphExecutor to support start_node_id, 
        # OR we just handle it here by passing a modified list? No, connections rely on full list.
        
        executor = GraphExecutor()
        
        # We need to tell Executor WHERE to start if start_node_id is set.
        # Implementation Detail: context could hold 'start_node_id'?
        # Or we temporarily modify Executor?
        
        # For now, let's update GraphExecutor in a separate tool call if needed, 
        # but actually, let's verify if we need it.
        # discord_manager calls it with start_node_id.
        
        # Hack: Validating start_node_id behavior
        if start_node_id:
            # We filter nodes_list to ensure we find this node? 
            # Or we modify GraphExecutor.execute to accept start_node_id.
            # Modify GraphExecutor.execute is cleaner. But I already wrote it.
            # I will modify GraphExecutor in next step.
            pass
            
        success = executor.execute(nodes_list, context, start_node_id=start_node_id)
        return success

    except Exception as e:
        log_message(f"Execution Error: {e}")
        return False
