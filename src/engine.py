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
        current_node = next((n for n in nodes_list if n.get('type') in ('start', 'bot/start')), None)
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
        node_type = current_node.get('type', '').replace('bot/', '')
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
                    c_val = int(props.get('count', 3))
                    # If 0, treat as infinite. We use -1 to represent infinite internally so 0 can be 'finished'.
                    if c_val == 0: c_val = -1
                    loop_states[node_id] = c_val
                    loop_stack.append(node_id)
                    log_message(f"Loop Start (Count: {'Infinite' if c_val == -1 else c_val})")
                
                count = loop_states[node_id]
                
                if count == -1:
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
                  # Nested script execution
                  script_name = props.get('scriptName')
                  import os
                  import json
                  
                  script_path = os.path.join('scripts', f"{script_name}.json")
                  if os.path.exists(script_path):
                      log_message(f"Calling Script: {script_name}")
                      try:
                          with open(script_path, 'r', encoding='utf-8') as f:
                              script_data = json.load(f)
                              
                          if isinstance(script_data, str):
                              try:
                                  script_data = json.loads(script_data)
                              except Exception as e:
                                  log_message(f"Error parsing script JSON string: {e}")
                                  script_data = {}
                          
                          # Graph Preprocessing (Links -> Next Pointers)
                          sub_actions = []
                          
                          # Check if it is a Raw LiteGraph with 'nodes' and 'links'
                          if isinstance(script_data, dict) and 'nodes' in script_data and 'links' in script_data:
                              nodes = script_data.get('nodes', [])
                              links = script_data.get('links', [])
                              
                              # Map links: origin_id -> { slot_index: target_node_id }
                              connections = {} 
                              link_map = { l[0]: l for l in links } # link_id -> link_data
                              
                              for link in links:
                                  # [id, origin_id, origin_slot, target_id, target_slot, type]
                                  if len(link) >= 6:
                                      origin_id = link[1]
                                      origin_slot = link[2]
                                      target_id = link[3]
                                      if origin_id not in connections: connections[origin_id] = {}
                                      connections[origin_id][origin_slot] = target_id
                                      
                              for node in nodes:
                                  node_type = node['type'].replace('bot/', '')
                                  new_node = {
                                      'id': node['id'],
                                      'type': node_type,
                                      'properties': node.get('properties', {}),
                                      'input_links': {}
                                  }
                                  
                                  # Outputs (Next Pointers)
                                  conns = connections.get(node['id'], {})
                                  if node_type == 'loop':
                                      new_node['next_body'] = conns.get(0)
                                      new_node['next_exit'] = conns.get(1)
                                  elif node_type == 'find_image':
                                       new_node['next_found'] = conns.get(0)
                                       new_node['next_not_found'] = conns.get(1)
                                  else:
                                       new_node['next'] = conns.get(0)
                                       
                                  # Inputs (Data Flow)
                                  if 'inputs' in node:
                                      for inp in node['inputs']:
                                          link_id = inp.get('link')
                                          if link_id and link_id in link_map:
                                              l = link_map[link_id]
                                              new_node['input_links'][inp['name']] = { 'id': l[1], 'slot': l[2] }
                                              
                                  sub_actions.append(new_node)

                          elif isinstance(script_data, dict) and 'actions' in script_data:
                              # Already processed format? (Not standard save but possibly from other sources)
                              sub_actions = script_data.get('actions', [])
                          elif isinstance(script_data, list):
                               # Legacy format?
                               sub_actions = script_data
                          
                          if sub_actions:
                              # Register Hooks for this sub-script
                              # We need to scan for 'discord_wait' nodes and register them.
                              # Note: This might overwrite existing hooks if command names collide.
                              registered_hooks = []
                              
                              # We need to traverse sub_actions to find wait nodes
                              for sub_node in sub_actions:
                                  sn_type = sub_node.get('type', '')
                                  if 'discord_wait' in sn_type: # Handles 'bot/discord_wait' and 'discord_wait'
                                      sn_id = sub_node['id']
                                      sn_props = sub_node.get('properties', {})
                                      sn_cmd = sn_props.get('command_name', 'continue').strip() or 'continue'
                                      
                                      # Register hook
                                      # check if exists
                                      if sn_cmd in shared.command_hooks:
                                          log_message(f"Warning: Sub-script command '/{sn_cmd}' overrides existing hook.")
                                      
                                      # Define signaler closure
                                      def make_signaler(nid, nm):
                                          def signaler():
                                              event = shared.wait_events.get(nid)
                                              if event:
                                                  log_message(f"Signaling event for node {nid} (from sub-script)")
                                                  event.set()
                                                  return True
                                              else:
                                                  log_message(f"Command '/{nm}' received, but WaitNode {nid} not ready.")
                                              return False
                                          return signaler
                                          
                                      handler = make_signaler(sn_id, sn_cmd)
                                      shared.command_hooks[sn_cmd] = handler
                                      registered_hooks.append(sn_cmd)
                                      log_message(f"Sub-script registered command: /{sn_cmd} -> Node {sn_id}")

                              try:
                                  # Recursive Call
                                  log_message(f"Starting Sub-script '{script_name}' execution...")
                                  success = execute_graph(sub_actions, recursion_depth=recursion_depth + 1)
                                  if not success:
                                      log_message(f"Sub-script '{script_name}' returned False.")
                                  else:
                                      log_message(f"Sub-script '{script_name}' finished normally.")
                              finally:
                                  # Cleanup registered hooks
                                  for cmd in registered_hooks:
                                      # Only remove if it's still our handler (in case of race/overwrite?)
                                      # For now simple pop
                                      shared.command_hooks.pop(cmd, None)
                                      log_message(f"Unregistered sub-script command: /{cmd}")
                                      
                          else:
                              log_message(f"Error: Script '{script_name}' seems empty or invalid format.")
                      except Exception as e:
                          log_message(f"Error loading/running script {script_name}: {e}")
                  else:
                      log_message(f"Error: Script file '{script_name}' not found.")
                      
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

            elif node_type == 'discord_screenshot':
                 msg = props.get('message', '')
                 import discord
                 import os
                 
                 temp_path = "temp_screenshot_discord.png"
                 # 1. Capture
                 try:
                    bot_instance.screencap(temp_path)
                 except Exception as e:
                    log_message(f"Screenshot capture failed: {e}")
                    # If capture fails, we still try to move on
                 
                 # 2. Send
                 if os.path.exists(temp_path):
                     try:
                         settings = load_settings()
                         uid = settings.get('user_id')
                         if shared.discord_client and uid:
                             async def _send_dm_img():
                                 try:
                                     await shared.discord_client.wait_until_ready()
                                     user = await shared.discord_client.fetch_user(int(uid))
                                     with open(temp_path, 'rb') as f:
                                         picture = discord.File(f, filename="screenshot.png")
                                         await user.send(content=msg, file=picture)
                                     log_message(f"Sent Screenshot to {uid}")
                                 except Exception as exc:
                                     log_message(f"Failed to send Screenshot: {exc}")
                             
                             if shared.discord_loop:
                                future = asyncio.run_coroutine_threadsafe(_send_dm_img(), shared.discord_loop)
                                try:
                                    future.result(timeout=20)
                                except Exception as fe:
                                    log_message(f"Discord Screenshot Timed Out/Failed: {fe}")
                             else:
                                 log_message("Discord loop not active.")
                         else:
                             log_message("Skipped Discord Screenshot: No client or User ID.")
                     except Exception as e:
                         log_message(f"Discord Screenshot Error: {e}")
                     
                     # Cleanup
                     try: os.remove(temp_path)
                     except: pass
                 
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
                 log_message(f"WaitNode {node_id}: Event created. LoopStack: {loop_stack}")
                 
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
                     log_message(f"WaitNode {node_id}: waiting done. Next ID: {next_id}")
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
                log_message(f"Auto-Loop Return to {next_id}")
                 
        except Exception as e:
            log_message(f"Exec Error ({node_type}): {e}")
            return False
            
        current_node = node_map.get(next_id)
        time.sleep(0.05)
    return True
