FROM python:3.12-slim

# 安裝中文字型 (matplotlib 產出 PDF 需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-noto-cjk \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker-entrypoint.sh

VOLUME ["/app/data", "/app/output"]

EXPOSE 5000

ENV FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
