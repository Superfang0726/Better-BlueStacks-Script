import sys
import os

# Add src to sys.path to ensure imports work correctly
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the main app logic
# Doing this after modifying sys.path ensures 'src' modules are importable 
# even if they use absolute imports assuming they are root, OR if they function as a package.
# Since we moved everything to src, and they likely import each other (e.g. "import shared"),
# we need 'src' to be treated as a path source.
from src.main import start_server

if __name__ == '__main__':
    start_server()
