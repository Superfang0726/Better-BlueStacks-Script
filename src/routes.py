from flask import render_template, request, jsonify
import threading
import os
import time
import json
import shared
from shared import log_message, log_lock, log_buffer
from engine import get_bot
from discord_manager import run_script
from settings import load_settings, save_settings

SCRIPTS_DIR = 'scripts'

def ensure_scripts_dir():
    if not os.path.exists(SCRIPTS_DIR):
        os.makedirs(SCRIPTS_DIR)

def get_image_tree(path_to_scan, relative_path=""):
    items = []
    if not os.path.exists(path_to_scan):
        return items
        
    for entry in sorted(os.listdir(path_to_scan)):
        full_path = os.path.join(path_to_scan, entry)
        rel_path = os.path.join(relative_path, entry).replace("\\", "/")
        
        if os.path.isdir(full_path):
            children = get_image_tree(full_path, rel_path)
            if children:
                items.append({
                    "name": entry,
                    "type": "folder",
                    "children": children
                })
        elif entry.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            items.append({
                "name": entry,
                "type": "file",
                "path": "images/" + rel_path
            })
    return items

def configure_routes(app):
    
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/logs')
    def get_logs():
        with log_lock:
            return jsonify({"logs": list(log_buffer)})

    @app.route('/run', methods=['POST'])
    def run():
        if shared.is_running:
            log_message("Error: Run request rejected - Script is already running.")
            return jsonify({"status": "error", "message": "Script is already running"}), 400
            
        data = request.json
        actions = data.get('actions', [])
        mode = data.get('mode', 'legacy')
        
        # Run in a separate thread so we don't block the server
        shared.current_thread = threading.Thread(target=run_script, args=(actions, mode))
        shared.current_thread.start()
        
        return jsonify({"status": "success", "message": "Script started"})

    @app.route('/stop', methods=['POST'])
    def stop():
        if shared.is_running:
            shared.is_running = False
            log_message("Stopping script...")
        else:
            log_message("Stop requested, but script was not running.")
            
        return jsonify({"status": "success", "message": "Stopping script..."})

    @app.route('/api/register_commands', methods=['POST'])
    def register_commands():
        """
        API to manually trigger Discord command registration.
        """
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        nodes_list = data.get("nodes", [])
        
        from discord_manager import register_commands_logic
        success = register_commands_logic(nodes_list)
        
        if success:
            return jsonify({"status": "success", "message": "Commands registered successfully."})
        else:
            return jsonify({"status": "error", "message": "Failed to register commands. Check server logs."}), 500


    @app.route('/shutdown', methods=['POST'])
    def shutdown():
        shared.is_running = False
        log_message("Server shutting down...")
        
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
        
        def force_exit():
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
                if not os.path.exists('static'):
                    os.makedirs('static')
                    
                filename = "static/capture.png"
                bot_instance.screencap(filename)
                
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
        try:
            if not os.path.exists('images'):
                os.makedirs('images')
                
            files = [f for f in os.listdir('images') if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
            return jsonify({"images": files})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/scripts', methods=['GET'])
    def list_scripts():
        ensure_scripts_dir()
        try:
            files = [f.replace('.json', '') for f in os.listdir(SCRIPTS_DIR) if f.endswith('.json')]
            return jsonify({"scripts": files})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/scripts', methods=['POST'])
    def save_script():
        ensure_scripts_dir()
        data = request.json
        name = data.get('name')
        content = data.get('content')
        
        if not name or not content:
            return jsonify({"error": "Missing name or content"}), 400
            
        try:
            filepath = os.path.join(SCRIPTS_DIR, f"{name}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            return jsonify({"status": "success", "message": f"Script '{name}' saved."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

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
        try:
            filepath = os.path.join(SCRIPTS_DIR, f"{name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                return jsonify({"status": "success", "message": f"Script '{name}' deleted."})
            else:
                return jsonify({"error": "Script not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/settings', methods=['GET', 'POST'])
    def handle_settings():
        if request.method == 'GET':
            settings = load_settings()
            return jsonify(settings)
        elif request.method == 'POST':
            new_data = request.json
            current_settings = load_settings()
            
            # Update generic fields
            for key, value in new_data.items():
                current_settings[key] = value
                
            if save_settings(current_settings):
                # Restart bot to apply new token OR new command list
                from discord_manager import start_bot_background, stop_bot
                
                # Check for commands update or token update
                # Simpler to just restart if anything distinct changes, or just always restart on save for simplicity
                stop_bot()
                # Give it a moment?
                start_bot_background(current_settings.get('discord_token'))
                
                return jsonify({"status": "success", "message": "Settings saved"})
            else:
                return jsonify({"status": "error", "message": "Failed to save settings"})

    @app.route('/api/logs/export', methods=['GET'])
    def export_logs():
        try:
            if os.path.exists("server.log"):
                # Use send_file to return the log file
                return send_file(os.path.abspath("server.log"), as_attachment=True, download_name="server.log")
            else:
                return "No log file found.", 404
        except Exception as e:
            return str(e), 500
