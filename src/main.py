from flask import Flask
from routes import configure_routes
from settings import load_settings
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Configure Routes
configure_routes(app)

def start_server():
    # Ensure images directory exists
    if not os.path.exists('images'):
        os.makedirs('images')
    
    # Load settings
    settings = load_settings()
    web_port = int(settings.get('web_port', 5000))
    
    # Start Discord Bot if token exists
    from discord_manager import start_bot_background
    start_bot_background()

    # Auto-open browser
    import webbrowser
    from threading import Timer
    
    def open_browser():
        webbrowser.open_new(f"http://127.0.0.1:{web_port}")
        
    Timer(1.5, open_browser).start()
    
    app.run(host='0.0.0.0', port=web_port, debug=False)

if __name__ == '__main__':
    start_server()
