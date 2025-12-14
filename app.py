from flask import Flask, render_template, request, jsonify
import threading
import time
from bluestacks_bot import BlueStacksBot, main as bot_main # We will need to refactor bot slightly

import sys
from collections import deque

app = Flask(__name__)

# Global log buffer
# Stores dicts: {"timestamp": <iso_str>, "message": <str>}
log_buffer = deque(maxlen=100)
log_lock = threading.Lock()

def log_message(message):
    """Log message to global buffer and stdout"""
    # Print to real stdout for server logs
    sys.__stdout__.write(f"{message}\n")
    sys.__stdout__.flush()
    
    with log_lock:
        # Use UTC timestamp for consistency, client converts to local
        import datetime
        ts = datetime.datetime.utcnow().isoformat() + 'Z'
        log_buffer.append({"timestamp": ts, "message": message})

# Global bot instance
bot = None
# Global execution control
is_running = False
current_thread = None

@app.route('/logs')
def get_logs():
    with log_lock:
        return jsonify({"logs": list(log_buffer)})

def start_adb_server():
    """Start local ADB server if not running"""
    import subprocess
    try:
        # Check if adb is sending replies
        # 檢查 ADB 是否有回應
        log_message("Checking/Starting ADB Server...")
        subprocess.run(["adb", "start-server"], check=True)
    except Exception as e:
        log_message(f"Failed to start ADB server: {e}")

def get_bot():
    global bot
    if bot is None:
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
        # 在這裡我們將 ADB_HOST 環境變數視為 DEVICE HOST
        device_host = os.environ.get("ADB_HOST", default_host)
        device_port = int(os.environ.get("ADB_PORT", 5555))
        
        # Use our direct logging function
        bot = BlueStacksBot(device_host=device_host, device_port=device_port, logger=log_message)
    return bot

    return bot

def execute_graph(nodes_list, recursion_depth=0):
    """
    Execute a list of nodes representing a flow graph.
    執行代表流程圖的節點列表。
    
    Args:
        nodes_list (list): List of node dictionaries from LiteGraph.
        recursion_depth (int): Current depth of recursion to prevent infinite loops.
    """
    global is_running
    if recursion_depth > 10:
        log_message("Error: Max recursion depth (10) reached.")
        return False
    
    node_map = { node['id']: node for node in nodes_list }
    loop_states = {} # {id: count}
    loop_stack = [] # [id1, id2] - For nested loops / 用於巢狀迴圈
    node_outputs = {} # { node_id: { slot_index: value } } - Data Flow / 資料流
    
    current_node = next((n for n in nodes_list if n.get('type') == 'start'), None)
    if not current_node:
        log_message("Error: No Start node.")
        return False
        
    try:
        bot_instance = get_bot()
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

    while current_node and is_running:
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

def run_script(actions, mode='graph'):
    """
    Main entry point for running a script.
    執行腳本的主要入口點。
    """
    global is_running
    is_running = True
    
    log_message(f"Starting execution...")
    
    try:
        # Check connection once before starting
        get_bot()
        
        # We only support graph execution now
        execute_graph(actions)
            
    except Exception as e:
        log_message(f"Script execution error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        is_running = False
        log_message("Script stopped.")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
def run():
    global is_running, current_thread
    
    if is_running:
        log_message("Error: Run request rejected - Script is already running.")
        return jsonify({"status": "error", "message": "Script is already running"}), 400
        
    data = request.json
    actions = data.get('actions', [])
    mode = data.get('mode', 'legacy')
    
    # Run in a separate thread so we don't block the server
    current_thread = threading.Thread(target=run_script, args=(actions, mode))
    current_thread.start()
    
    return jsonify({"status": "success", "message": "Script started"})

@app.route('/stop', methods=['POST'])
def stop():
    global is_running
    if is_running:
        is_running = False
        log_message("Stopping script...")
    else:
        log_message("Stop requested, but script was not running.")
        
    return jsonify({"status": "success", "message": "Stopping script..."})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    global is_running
    is_running = False
    log_message("Server shutting down...")
    
    # Terminate the server
    # 關閉伺服器
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    
    # Force kill the process after a brief delay ensuring response is sent
    def force_exit():
        import time, os
        time.sleep(1)
        os._exit(0)
        
    threading.Thread(target=force_exit).start()
    
    return jsonify({"status": "success", "message": "Server shutting down..."})

@app.route('/test_connection', methods=['POST'])
def test_connection():
    log_message("Received Test Connection request...")
    try:
        bot_instance = get_bot()
        if bot_instance.device:
            bot_instance.home()
            return jsonify({"status": "success", "message": "已發送 Home 鍵指令 (Sent HOME Command)"})
        else:
            return jsonify({"status": "error", "message": "無法連接到設備 (Device not connected)"}), 500
    except Exception as e:
        log_message(f"Test connection failed: {e}")
        return jsonify({"status": "error", "message": f"Error: {e}"}), 500

@app.route('/capture', methods=['POST'])
def capture():
    try:
        bot_instance = get_bot()
        if bot_instance.device:
            import os
            import time
            if not os.path.exists('static'):
                os.makedirs('static')
                
            # Capture to static folder
            filename = "static/capture.png"
            bot_instance.screencap(filename)
            
            # Return URL with timestamp to prevent caching
            return jsonify({
                "status": "success", 
                "url": f"/{filename}?t={int(time.time())}"
            })
        else:
            return jsonify({"status": "error", "message": "無法連接到設備 (Device not connected)"}), 500
    except Exception as e:
        log_message(f"Capture failed: {e}")
        return jsonify({"status": "error", "message": f"Error: {e}"}), 500

@app.route('/images', methods=['GET'])
def list_images():
    import os
    try:
        if not os.path.exists('images'):
            os.makedirs('images')
            
        files = [f for f in os.listdir('images') if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        return jsonify({"images": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Script Storage API ---
SCRIPTS_DIR = 'scripts'

def ensure_scripts_dir():
    import os
    if not os.path.exists(SCRIPTS_DIR):
        os.makedirs(SCRIPTS_DIR)

@app.route('/api/scripts', methods=['GET'])
def list_scripts():
    ensure_scripts_dir()
    import os
    try:
        files = [f.replace('.json', '') for f in os.listdir(SCRIPTS_DIR) if f.endswith('.json')]
        return jsonify({"scripts": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scripts', methods=['POST'])
def save_script():
    ensure_scripts_dir()
    import os
    import json
    data = request.json
    name = data.get('name')
    content = data.get('content') # The array of actions
    
    if not name or not content:
        return jsonify({"error": "Missing name or content"}), 400
        
    try:
        filepath = os.path.join(SCRIPTS_DIR, f"{name}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success", "message": f"Script '{name}' saved."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper for recursive image listing
def get_image_tree(path_to_scan, relative_path=""):
    items = []
    if not os.path.exists(path_to_scan):
        return items
        
    for entry in sorted(os.listdir(path_to_scan)):
        full_path = os.path.join(path_to_scan, entry)
        rel_path = os.path.join(relative_path, entry).replace("\\", "/") # Web paths
        
        if os.path.isdir(full_path):
            children = get_image_tree(full_path, rel_path)
            if children: # Only add if has content
                items.append({
                    "name": entry,
                    "type": "folder",
                    "children": children
                })
        elif entry.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            items.append({
                "name": entry,
                "type": "file",
                "path": "images/" + rel_path # Full path for bot usage, relative to project root?
                # Actually, verify how bot uses it. Bot expects path relative to CWD or absolute.
                # Project root is CWD. So "images/sub/foo.png" is good.
                # BUT, find_and_click usually expects "images/..."
            })
    return items

@app.route('/api/images', methods=['GET'])
def api_list_images():
    img_dir = os.path.join(os.getcwd(), 'images')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
    
    tree = get_image_tree(img_dir)
    return jsonify({"images": tree})

@app.route('/api/scripts/<name>', methods=['GET'])
def load_script(name):
    ensure_scripts_dir()
    import os
    import json
    try:
        filepath = os.path.join(SCRIPTS_DIR, f"{name}.json")
        if not os.path.exists(filepath):
             return jsonify({"error": "Script not found"}), 404
             
        with open(filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scripts/<name>', methods=['DELETE'])
def delete_script(name):
    ensure_scripts_dir()
    import os
    try:
        filepath = os.path.join(SCRIPTS_DIR, f"{name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"status": "success", "message": f"Script '{name}' deleted."})
        else:
            return jsonify({"error": "Script not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure images directory exists
    import os
    if not os.path.exists('images'):
        os.makedirs('images')
    
    # Disable debug mode to prevent reloader and multiple instances
    app.run(host='0.0.0.0', port=5000, debug=False)
