# BlueStacks Visual Scripting Automation

這是一個基於 Web 的可視化自動化工具，專為 BlueStacks 模擬器設計。透過直觀的節點編輯器 (Node Editor)，您可以輕鬆設拖拉並連接節點來建立自動化腳本，無需編寫複雜的程式碼。

## ✨ 主要功能

- **可視化腳本編輯**：使用 LiteGraph.js 構建的直觀介面，透過連線控制執行流程。
- **強大的執行引擎**：
  - **ADB 控制**：支援後台執行點擊 (Click) 與滑動 (Swipe)。
  - **智慧找圖 (Find Image)**：
    - **Auto 模式**：優先使用 SIFT (抗旋轉/縮放)，失敗自動切換至 Template Matching (精確比對)。
    - **手動模式**：可指定 SIFT 或 Template Matching。
    - **資料流 (Data Flow)**：找到的座標 (X, Y) 可直接傳遞給點擊或滑動節點。
- **邏輯控制**：
  - **迴圈 (Loop)**：支援指定次數或是無限迴圈 (0)。
  - **中斷 (Break)**：條件式跳出迴圈。
  - **巢狀腳本 (Run Script)**：可呼叫其他已儲存的腳本，實現模組化設計。
- **即時監控與工具**：
  - **網頁介面**：瀏覽器即開即用 (預設 Port 5000)。
  - **螢幕截圖**：即時預覽遊戲畫面。
  - **座標拾取**：點擊預覽圖即可自動填入座標。
  - **腳本管理**：線上儲存、載入與管理腳本。

## 🚀 快速開始

### 方法一：使用 Docker (推薦)

只需雙擊執行專案目錄下的 `setup_docker.bat` 檔案。
它會自動建置環境並啟動服務，完成後請瀏覽器打開 `http://localhost:5000`。

### 方法二：手動執行 (Python)

1.  **安裝依賴**：
    ```bash
    pip install -r requirements.txt
    ```
2.  **執行伺服器**：
    ```bash
    python run.py
    ```
3.  **打開瀏覽器**：
    訪問 `http://127.0.0.1:5000`。

## 🛠️ 介面說明

1.  **Toolbar (上方工具列)**：
    - **執行 (Run)**：開始執行當前畫布上的腳本。
    - **停止 (Stop)**：強制停止執行。
    - **清空 (Clear)**：清除畫布所有節點。
    - **儲存/載入**：管理您的腳本檔案。

2.  **Sidebar (左側選單)**：
    - **流程控制**：Start, Wait, Loop, Break, Call Script。
    - **基本動作**：Click, Swipe。
    - **視覺辨識**：Find Image (支援 SIFT/Template)。

3.  **Canvas (中間畫布)**：
    - 拖拉節點進行編輯。
    - **Delete/Backspace**：刪除選取的節點。

4.  **Monitor (右側面板)**：
    - **預覽畫面**：顯示截圖與滑鼠座標。
    - **測試連線**：發送 Home 鍵測試 ADB 連接。
    - **Log Console**：顯示執行日誌與錯誤訊息。

## 📝 節點介紹

| 節點類型 | 描述 |
| :--- | :--- |
| **Start** | 腳本的起點，必須存在。 |
| **Wait** | 等待指定秒數。 |
| **Loop** | 迴圈區塊。`Body` 輸出執行內容，`Exit` 輸出迴圈結束後的路徑。Count設為 0 為無限迴圈。 |
| **Find Image** | 在畫面搜尋圖片。支援 `Auto`, `SIFT`, `Template` 演算法。輸出 `Found` 或 `Not Found` 路徑，以及 `X`, `Y` 座標。 |
| **Click** | 點擊指定座標。可接收來自 `Find Image` 的 (X, Y) 輸入。 |
| **Swipe** | 執行滑動操作。 |
| **Call Script** | 執行另一個已儲存的 JSON 腳本。 |

## ADB 設定

請確保 BlueStacks 已啟用 ADB：
1.  進入 BlueStacks 設定 > 進階 (Advanced)。
2.  勾選「啟用 Android Debug Bridge (ADB)」。
3.  預設連接 `127.0.0.1:5555`。若 Port 不同，請設定環境變數 `ADB_PORT`。
