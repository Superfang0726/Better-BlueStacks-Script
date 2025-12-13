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

def execute_actions(actions, recursion_depth=0):
    """
    Recursive function to execute a list of actions.
    Returns True if finished normally, False if stopped/error.
    """
    global is_running
    
    # Prevent infinite recursion / stack overflow
    if recursion_depth > 10:
        log_message("Error: Max recursion depth (10) reached. Stopping.")
        return False

    i = 0
    loop_stack = [] # Stores {index: int, count: int}
    import os
    import json
    
    try:
        # We need a bot instance. It should be initialized by the entry point, 
        # but get_bot() is safe to call multiple times (returns singleton).
        bot_instance = get_bot()
    except Exception as e:
        log_message(f"Failed to get bot: {e}")
        return False

    while i < len(actions) and is_running:
        if not is_running:
            return False
            
        action = actions[i]
        act_type = action.get('type')
        
        if act_type == 'click':
            bot_instance.click(int(action['x']), int(action['y']))
            
        elif act_type == 'swipe':
            bot_instance.swipe(
                int(action['x1']), int(action['y1']), 
                int(action['x2']), int(action['y2']), 
                int(action.get('duration', 500))
            )
            
        elif act_type == 'wait':
            log_message(f"Waiting for {action['seconds']} seconds...")
            time.sleep(float(action['seconds']))
            
        elif act_type == 'find_click':
            img_path = action['template']
            bot_instance.find_and_click(img_path)

        elif act_type == 'loop_start':
            # Count 0 means infinite, treated as -1 in stack
            raw_count = int(action['count'])
            count = -1 if raw_count == 0 else raw_count
            
            # If stack top is current index, it means we looped back.
            # Don't re-push.
            is_reentry = False
            if loop_stack and loop_stack[-1]['index'] == i:
                is_reentry = True
                
            if not is_reentry:
                # If count is > 0 OR -1 (infinite), enter loop
                if count != 0: 
                    loop_stack.append({'index': i, 'count': count})
                    msg = "Infinite" if count == -1 else count
                    log_message(f"Entering loop (count: {msg})")
                else:
                    pass

        elif act_type == 'loop_end':
            if loop_stack:
                current_loop = loop_stack[-1]
                
                should_loop = False
                if current_loop['count'] == -1:
                    should_loop = True
                else:
                    current_loop['count'] -= 1
                    if current_loop['count'] > 0:
                        should_loop = True
                
                if should_loop:
                    i = current_loop['index']
                    msg = "Infinite" if current_loop['count'] == -1 else current_loop['count']
                    log_message(f"Looping back... ({msg} left)")
                else:
                    loop_stack.pop()
                    log_message("Loop finished.")
            else:
                log_message("Warning: loop_end without loop_start")

        elif act_type == 'loop_break':
            if loop_stack:
                log_message("Breaking out of loop...")
                loop_stack.pop()
                depth = 1 
                k = i + 1
                found_end = False
                while k < len(actions):
                    at = actions[k].get('type')
                    if at == 'loop_start':
                        depth += 1
                    elif at == 'loop_end':
                        depth -= 1
                        if depth == 0:
                            i = k 
                            found_end = True
                            break
                    k += 1
                if not found_end:
                        log_message("Error: Could not find loop_end for break")
                        break
            else:
                log_message("Warning: loop_break called outside of loop")

        elif act_type == 'if_found':
            img_path = action['template']
            condition = action.get('condition', 'found') # 'found' or 'not_found'
            click_target = action.get('click_target', True) # Default True
            
            log_key = "If Found" if condition == 'found' else "If Not Found"
            log_message(f"Checking {log_key}: {img_path} (Click: {click_target})")
            
            found = bot_instance.find_and_click(img_path, click_target=click_target)
            
            # Logic:
            # 1. condition='found', found=True -> Enter (skip=False)
            # 2. condition='found', found=False -> Skip (skip=True)
            # 3. condition='not_found', found=True -> Skip (skip=True)
            # 4. condition='not_found', found=False -> Enter (skip=False)
            
            should_enter = False
            if condition == 'found':
                should_enter = found
            else:
                should_enter = not found
            
            if not should_enter:
                # log_message("Condition False. Skipping...") # Reduce spam
                depth = 1
                j = i + 1
                found_end = False
                while j < len(actions):
                    if actions[j]['type'] == 'if_found':
                        depth += 1
                    elif actions[j]['type'] == 'if_end':
                        depth -= 1
                        if depth == 0:
                            i = j
                            found_end = True
                            break
                    j += 1
                if not found_end:
                    log_message("Error: Missing if_end")
                    break
            else:
                log_message(f"Condition Met ({log_key}). Entering block.")

        elif act_type == 'if_end':
            pass

        elif act_type == 'run_script':
            script_name = action.get('script_name')
            log_message(f"Calling sub-script: {script_name}")
            
            filepath = os.path.join(SCRIPTS_DIR, f"{script_name}.json")
            if os.path.exists(filepath):
                 try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        sub_actions = json.load(f)
                    
                    # Clean recursion
                    result = execute_actions(sub_actions, recursion_depth + 1)
                    if not result:
                        # If sub-script failed or stopped, we stop too
                        return False
                    log_message(f"Sub-script {script_name} finished.")
                 except Exception as e:
                     log_message(f"Error executing sub-script {script_name}: {e}")
            else:
                log_message(f"Error: Script {script_name} not found.")

        time.sleep(0.5) # Small delay between steps
        i += 1
        
    return True

def run_script(actions):
    global is_running
    is_running = True
    
    log_message("Starting script execution...")
    
    try:
        # Check connection once before starting
        get_bot()
        
        execute_actions(actions)
            
    except Exception as e:
        log_message(f"Script execution error: {e}")
    finally:
        is_running = False
        log_message("Script stopped.") # Changed to 'Stopped' as requested

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
    
    # Run in a separate thread so we don't block the server
    current_thread = threading.Thread(target=run_script, args=(actions,))
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
