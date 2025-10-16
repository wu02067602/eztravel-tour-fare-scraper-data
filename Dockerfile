# 使用 Chainguard Python 開發映像
FROM asia-east1-docker.pkg.dev/testing-cola-rd/chainguard-images/python:latest-dev

# 切換到 root 用戶以執行需要權限的操作
USER root

# 設置環境變數
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USE_POSIX_PATH=1 
    # GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-service-account-key.json

# 創建應用目錄和日誌目錄，並設置正確的權限
RUN mkdir -p /app/logs && \
    chown -R nonroot:nonroot /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/logs

# 設置工作目錄
WORKDIR /app

# # 複製 GCP 服務帳戶金鑰
# COPY testing-cola-rd-d50ed0fd3e07.json /app/gcp-service-account-key.json

# # 設置金鑰文件權限並確保 nonroot 用戶可以讀取
# RUN chown nonroot:nonroot /app/gcp-service-account-key.json && \
#     chmod 600 /app/gcp-service-account-key.json

# 切換回 nonroot 用戶
USER nonroot

# 複製 requirements.txt
COPY requirements.txt .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 暴露端口
EXPOSE 80

# 設置運行指令
ENTRYPOINT ["/bin/bash", "-c", "python eztravel_travel_crawler/main.py"]