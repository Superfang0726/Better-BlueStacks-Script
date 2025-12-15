import time
import asyncio
from bluestacks_bot import BlueStacksBot
import shared
from shared import log_message
from settings import load_settings

def start_adb_server():
    """Start local ADB server if not running"""
    import subprocess
    try:
        # Check if adb is sending replies
        log_message("Checking/Starting ADB Server...")
        subprocess.run(["adb", "start-server"], check=True)
    except FileNotFoundError:
        # Try BlueStacks ADB
        bs_adb = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
        import os
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
        # Ensure ADB server is running
        start_adb_server()
        
        # Initialize with settings. 
        # ADB Server is always 127.0.0.1:5037
        import os
        # Device host depends on environment
        # If running in Docker, device is on host.docker.internal
        # If running locally, device is on 127.0.0.1
        default_host = "host.docker.internal" if os.environ.get("ADB_HOST") == "host.docker.internal" else "127.0.0.1"
        
        # We use ADB_HOST env var as the DEVICE host now, or default to localhost logic
        device_host = os.environ.get("ADB_HOST", default_host)
        device_port = int(os.environ.get("ADB_PORT", 5555))
        
        # Use our direct logging function
        bot_instance = BlueStacksBot(device_host=device_host, device_port=device_port, logger=log_message)
    return bot_instance

def execute_graph(nodes_list, recursion_depth=0, start_node_id=None):
    """
    Execute a list of nodes representing a flow graph.
    執行代表流程圖的節點列表。
    
    Args:
        nodes_list (list): List of node dictionaries from LiteGraph.
        recursion_depth (int): Current depth of recursion to prevent infinite loops.
        start_node_id (int): Optional ID to start execution from (for events).
    """
    
    if recursion_depth > 10:
        log_message("Error: Max recursion depth (10) reached.")
        return False
    
    node_map = { node['id']: node for node in nodes_list }
    loop_states = {} # {id: count}
    loop_stack = [] # [id1, id2] - For nested loops / 用於巢狀迴圈
    node_outputs = {} # { node_id: { slot_index: value } } - Data Flow / 資料流
    
    current_node = None
    if start_node_id:
        current_node = node_map.get(start_node_id)
        if not current_node:
             log_message(f"Error: Start node {start_node_id} not found.")
             return False
    else:
        current_node = next((n for n in nodes_list if n.get('type') == 'start'), None)
        if not current_node:
            # It is okay to have no start node if we are in event mode (handled by caller), 
            # but if execute_graph is called without start_node_id, it usually means we expect one.
            log_message("Warning: No Start node found in main flow.")
            return False
        
    try:
        # We need to maintain the singleton bot if we want connection reuse, 
        # but for now we re-get it. Ideally shared.bot should be used.
        from shared import bot
        bot_instance = get_bot(bot)
        # Update global bot if it was None
        import shared
        shared.bot = bot_instance
    except Exception as e:
        log_message(f"Failed to get bot: {e}")
        return False
        
    def get_input_value(node, input_name, default_val):
        """
        Retrieve input value from connected nodes (Data Flow).
        從連接的節點獲取輸入值 (資料流)。
        """
        links = node.get('input_links', {})
        if input_name in links:
            link = links[input_name]
            src_id = link['id']
            slot = link['slot']
            if src_id in node_outputs and slot in node_outputs[src_id]:
                return node_outputs[src_id][slot]
        return default_val

    # Need to check shared.is_running
    while current_node and shared.is_running:
        node_id = current_node['id']
        node_type = current_node.get('type')
        props = current_node.get('properties', {})
        next_id = None
        
        try:
            if node_type == 'start':
                # Start node just moves to next
                # 開始節點僅移動到下一個
                next_id = current_node.get('next')
                
            elif node_type == 'click':
                # Click with optional Data Flow overriding properties
                # 點擊，可選的資料流覆蓋屬性
                x = int(get_input_value(current_node, 'X', props.get('x', 500)))
                y = int(get_input_value(current_node, 'Y', props.get('y', 500)))
                bot_instance.click(x, y)
                next_id = current_node.get('next')
                
            elif node_type == 'swipe':
                x1 = int(get_input_value(current_node, 'X1', props.get('x1', 500)))
                y1 = int(get_input_value(current_node, 'Y1', props.get('y1', 800)))
                x2 = int(get_input_value(current_node, 'X2', props.get('x2', 500)))
                y2 = int(get_input_value(current_node, 'Y2', props.get('y2', 200)))
                dur = int(props.get('duration', 500))
                bot_instance.swipe(x1, y1, x2, y2, dur)
                next_id = current_node.get('next')
                
            elif node_type == 'wait':
                sec = float(props.get('seconds', 1.0))
                log_message(f"Waiting {sec}s...")
                time.sleep(sec)
                next_id = current_node.get('next')
                
            elif node_type == 'find_image':
                template = props.get('template', '')
                algorithm = props.get('algorithm', 'auto')
                
                if template:
                    log_message(f"Checking: {template} (Algo: {algorithm})")
                    # Use bot's smart finder with selected algorithm
                    # 使用機器人的智慧搜尋 (帶演算法選擇)
                    center = bot_instance.find_and_click(template, click_target=False, method=algorithm)
                        
                    if center:
                        log_message(f"Found {template} at {center}")
                        # Store outputs for Data Flow (X, Y)
                        # 儲存資料流輸出 (X, Y)
                        if node_id not in node_outputs: node_outputs[node_id] = {}
                        node_outputs[node_id][2] = center[0] # Slot 2: X
                        node_outputs[node_id][3] = center[1] # Slot 3: Y
                        
                        next_id = current_node.get('next_found')
                    else:
                        log_message(f"Not found: {template}")
                        next_id = current_node.get('next_not_found')
                else:
                    next_id = current_node.get('next_not_found')
                    
            elif node_type == 'loop':
                if node_id not in loop_states:
                    loop_states[node_id] = int(props.get('count', 3))
                    loop_stack.append(node_id)
                    log_message(f"Loop Start (Count: {loop_states[node_id]})")
                count = loop_states[node_id]
                if count == 0:
                     # Infinite Loop / 無限迴圈
                     next_id = current_node.get('next_body')
                elif count > 0:
                     loop_states[node_id] -= 1
                     log_message(f"Looping... ({loop_states[node_id]} left)")
                     next_id = current_node.get('next_body')
                else:
                     log_message("Loop Finished.")
                     if loop_stack and loop_stack[-1] == node_id: loop_stack.pop()
                     loop_states.pop(node_id, None)
                     next_id = current_node.get('next_exit')
                     
            elif node_type == 'loop_break':
                log_message("Loop Break...")
                if loop_stack:
                    target = loop_stack.pop() # Pop current loop from stack
                    loop_states.pop(target, None) # Clear state
                    t_node = node_map.get(target)
                    next_id = t_node.get('next_exit') if t_node else None
                    log_message("Jumped to Loop Exit.")
                else:
                    log_message("Break outside loop ignored.")
                    next_id = current_node.get('next')
                    
            elif node_type == 'script':
                  # Nested script execution (Placeholder for now)
                  # 巢狀腳本執行 (目前暫位)
                  log_message(f"Script call '{props.get('scriptName')}' - not executed.")
                  next_id = current_node.get('next')

            elif node_type == 'discord_send':
                 msg = props.get('message', '')
                 try:
                     settings = load_settings()
                     uid = settings.get('user_id')
                     if shared.discord_client and uid:
                         async def _send_dm():
                             try:
                                 # Ensure bot is ready before fetching user
                                 await shared.discord_client.wait_until_ready()
                                 user = await shared.discord_client.fetch_user(int(uid))
                                 await user.send(msg)
                                 log_message(f"Sent DM to {uid}: {msg}")
                             except Exception as exc:
                                 log_message(f"Failed to send DM: {exc}")
                         
                         if shared.discord_loop:
                            future = asyncio.run_coroutine_threadsafe(_send_dm(), shared.discord_loop)
                            # Wait for the message to be sent before moving to next node!
                            try:
                                future.result(timeout=15)
                            except Exception as fe:
                                log_message(f"Discord Send Timed Out/Failed: {fe}")
                         else:
                             log_message("Discord loop not active.")
                     else:
                         log_message("Skipped Discord Send: No client or User ID.")
                 except Exception as e:
                     log_message(f"Discord Send Error: {e}")
                 next_id = current_node.get('next')

            elif node_type == 'discord_slash':
                 # Should not be encountered in normal flow usually, unless chained
                 # 一般流程不應遇到，除非串接
                 next_id = current_node.get('next')

            elif node_type == 'discord_wait':
                 import threading
                 cmd_name = props.get('command_name', 'continue')
                 log_message(f"Waiting for Discord command: /{cmd_name} ...")
                 
                 # Create event
                 event = threading.Event()
                 shared.wait_events[node_id] = event
                 
                 # Wait (Blocking)
                 # We can add a timeout if needed, but for now infinite or essentially infinite
                 # If user stops script, shared.is_running becomes False, but we are stuck in event.wait()
                 # So we should wait in chunks
                 
                 wait_success = False
                 while shared.is_running:
                     if event.wait(timeout=1.0):
                         wait_success = True
                         break
                 
                 # Clean up
                 shared.wait_events.pop(node_id, None)
                 
                 if wait_success:
                     log_message(f"Resumed by command /{cmd_name}")
                     next_id = current_node.get('next')
                 else:
                     log_message("Wait cancelled (Script Stopped).")
                     return False

            else:
                  next_id = current_node.get('next')                 
            # Automatic Loop Return: If end of branch and inside a loop, go back to loop start
            # 自動迴圈返回：若分支結束且在迴圈內，回到迴圈起點
            if next_id is None and loop_stack:
                # log_message(f"End of branch, returning to loop {loop_stack[-1]}")
                next_id = loop_stack[-1]
                 
        except Exception as e:
            log_message(f"Exec Error ({node_type}): {e}")
            return False
            
        current_node = node_map.get(next_id)
        time.sleep(0.05)
    return True
