from flask import Flask
from routes import configure_routes
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Configure Routes
configure_routes(app)

def start_server():
    # Ensure images directory exists
    # If run.py is caught as root, images will be in root, which is correct (../images relative to src?)
    # No, workdir is usually root, so 'images' is fine if CWD is project root.
    if not os.path.exists('images'):
        os.makedirs('images')
    
    # Start Discord Bot if token exists
    from discord_manager import start_bot_background
    start_bot_background()

    # Disable debug mode to prevent reloader and multiple instances locking ADB
    
    # Auto-open browser
    import webbrowser
    from threading import Timer
    
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000")
        
    Timer(1.5, open_browser).start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    start_server()
