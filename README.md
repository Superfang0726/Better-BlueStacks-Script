# BlueStacks 自動化腳本

這是一個用於在後台與 BlueStacks 模擬器進行交互的 Python 腳本。它使用 ADB (Android Debug Bridge) 協議，可以在不將模擬器視窗置頂的情況下執行點擊、滑動和截圖等操作。

## 功能

- **後台執行**：無需將模擬器畫面顯示在最上層即可操作。
- **ADB 連接**：透過網路端口連接到 BlueStacks。
- **基本操作**：支援點擊 (Click)、滑動 (Swipe)、輸入文字 (Send Text) 和截圖 (Screenshot)。
- **Docker 支援**：提供 Docker 環境，方便快速部署。

## 前置需求

在使用此腳本之前，請確保您已完成以下設置：

1.  **安裝 BlueStacks**：請確保已安裝並啟動 BlueStacks 模擬器。
2.  **啟用 ADB**：
    - 打開 BlueStacks 設定。
    - 進入「進階」 (Advanced) 標籤。
    - 勾選「啟用 Android Debug Bridge (ADB)」 (Enable Android Debug Bridge)。
    - 記下顯示的 IP 和 Port (通常是 `127.0.0.1:5555`)。

## 使用方法

### 方法一：使用自動化腳本 (推薦)

只需雙擊執行專案目錄下的 `setup_docker.bat` 檔案。
它會自動檢查 Docker 是否運行，並執行建置與啟動的所有步驟。

### 方法二：手動使用 Docker 指令

如果您習慣使用命令行，也可以手動執行：

1.  **啟動容器**：
    在專案目錄下打開終端機，執行：
    ```bash
    docker-compose up --build
    ```
    這將會建置並啟動包含 Python 環境和 ADB 的容器。腳本會自動嘗試連接到宿主機 (Host) 上的 BlueStacks。

2.  **查看日誌**：
    您可以從終端機輸出中看到連接狀態和測試操作的結果。

### 方法二：直接使用 Python 執行

如果您不想使用 Docker，可以直接在電腦上執行。

1.  **安裝依賴**：
    確保您已安裝 Python 3.9+，然後執行：
    ```bash
    pip install -r requirements.txt
    ```
    *注意：您可能需要手動安裝 `adb` 執行檔並將其加入系統 PATH 環境變數中，或者使用 BlueStacks 內建的 `hd-adb.exe`。*

2.  **設定連接**：
    修改 `bluestacks_bot.py` 中的 `host` 和 `port`，或是設定環境變數：
    - Windows PowerShell:
      ```powershell
      $env:ADB_HOST="127.0.0.1"
      $env:ADB_PORT="5555"
      python bluestacks_bot.py
      ```

## 檔案說明

- `setup_docker.bat`: Windows 自動化安裝與執行腳本 (點擊即用)。
- `bluestacks_bot.py`: 主要的 Python 腳本，包含 `BlueStacksBot` 類別和測試邏輯。
- `Dockerfile`: 用於建置 Docker 映像檔的設定。
- `docker-compose.yml`: Docker Compose 設定檔，定義了服務和網路連接。
- `requirements.txt`: Python 相依套件列表。

## 常見問題

- **無法連接到 BlueStacks？**
    - 確保 BlueStacks 正在運行。
    - 確保已在 BlueStacks 設定中啟用 ADB。
    - 檢查 Port 是否正確 (BlueStacks 不同實例可能會使用不同 Port，如 5555, 5565 等)。
    - 如果使用 Docker，確保 `host.docker.internal` 能正確解析到宿主機 IP。
