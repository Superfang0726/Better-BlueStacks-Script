# Use official Python 3.9 slim image to keep container size small
# 使用官方 Python 3.9 slim 映像檔以保持容器大小輕量
FROM python:3.9-slim

# Prevent Python from writing pyc files to disc
# 防止 Python 將 pyc 檔案寫入硬碟
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent Python from buffering stdout and stderr
# 防止 Python 緩衝標準輸出和標準錯誤輸出 (即時顯示 log)
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
# 設定容器內的工作目錄
WORKDIR /app

# Install system dependencies including adb and OpenCV requirements
# 安裝系統依賴，包含 adb 和 OpenCV 所需庫
RUN apt-get update && apt-get install -y \
    android-tools-adb \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
# 將需求檔案複製到容器中
COPY requirements.txt .

# Install Python dependencies
# 安裝 Python 依賴套件
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# 複製其餘的應用程式代碼
COPY . .

# Expose the Flask port
# 公開 Flask 連接埠
EXPOSE 5000

# Command to run the application
# 執行應用程式的指令
CMD ["python", "run.py"]
