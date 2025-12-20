# Better-BlueStacks-Script

A web-based visual automation tool designed for BlueStacks emulator. Using an intuitive Node Editor, you can easily drag, drop, and connect nodes to create automation scripts without writing complex code.

## ✨ Features

- **Visual Script Editing**: Intuitive interface built with LiteGraph.js, control execution flow through connections.
- **Powerful Execution Engine**:
  - **ADB Control**: Background click and swipe operations.
  - **Smart Image Finding (Find Image)**:
    - **Auto Mode**: Prioritizes SIFT (rotation/scale invariant), falls back to Template Matching.
    - **Manual Mode**: Choose between SIFT or Template Matching.
    - **Data Flow**: Found coordinates (X, Y) can be passed to Click or Swipe nodes.
  - **Pixel Color Detection (Check Pixel)**: Check if a specific coordinate matches a target color, with tolerance support.
- **Logic Control**:
  - **Loop**: Supports fixed count or infinite loop (set to 0).
  - **Break**: Conditionally exit loops.
  - **Nested Scripts (Call Script)**: Execute other saved scripts for modular design.
- **Discord Integration**:
  - **Send Message**: Send Discord notifications during script execution.
  - **Wait Command**: Control script flow remotely via Discord slash commands.
  - **Screenshot**: Capture and send game screenshots to Discord.
- **Real-time Monitoring & Tools**:
  - **Web Interface**: Browser-ready (default Port 5000).
  - **Screen Capture**: Live preview of game screen.
  - **Coordinate & Color Picker**: Click on preview to auto-fill coordinates and color values.
  - **Script Management**: Save, load, and manage scripts online.

## 🚀 Quick Start

### Method 1: Using Docker (Recommended)

Simply double-click `setup_docker.bat` in the project directory.
It will automatically build the environment and start the service. Open `http://localhost:5000` in your browser.

### Method 2: Manual Execution (Python)

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run Server**:
    ```bash
    python run.py
    ```
3.  **Open Browser**:
    Navigate to `http://127.0.0.1:5000`.

## 🛠️ Interface Guide

1.  **Toolbar (Top)**:
    - **Run**: Start executing the current canvas script.
    - **Stop**: Force stop execution.
    - **Clear**: Clear all nodes from canvas.
    - **Save/Load**: Manage your script files.

2.  **Sidebar (Left)**:
    - **Flow Control**: Start, Wait, Loop, Break, Call Script.
    - **Basic Actions**: Click, Swipe, Home, Recent Apps.
    - **Vision**: Find Image, Check Pixel.
    - **Discord**: Send Message, Wait Command, Screenshot.

3.  **Canvas (Center)**:
    - Drag and drop nodes for editing.
    - **Delete/Backspace**: Remove selected nodes.

4.  **Monitor (Right Panel)**:
    - **Preview**: Display screenshots and mouse coordinates.
    - **Test Connection**: Send Home key to test ADB connection.
    - **Log Console**: Show execution logs and error messages.

## 📝 Node Reference

| Node Type | Description |
| :--- | :--- |
| **Start** | Entry point of the script. Required. |
| **Wait** | Wait for specified seconds. |
| **Loop** | Loop block. `Body` output for loop content, `Exit` for post-loop path. Count 0 = infinite. |
| **Find Image** | Search for image on screen. Supports `Auto`, `SIFT`, `Template` algorithms. Outputs `Found` or `Not Found`, plus `X`, `Y` coordinates. |
| **Check Pixel** | Check if pixel color at coordinates matches. Supports tolerance. Outputs `Found` or `Not Found`. |
| **Click** | Click at specified coordinates. Can receive (X, Y) from `Find Image`. |
| **Swipe** | Perform swipe operation. |
| **Call Script** | Execute another saved JSON script. |
| **Discord Send** | Send message to Discord. |
| **Discord Wait** | Wait for Discord slash command trigger to continue. |
| **Discord Screenshot** | Capture screen and send to Discord. |

## ADB Setup

Ensure ADB is enabled in BlueStacks:
1.  Go to BlueStacks Settings > Advanced.
2.  Enable "Android Debug Bridge (ADB)".
3.  Default connection: `127.0.0.1:5555`. Set `ADB_PORT` environment variable if different.
