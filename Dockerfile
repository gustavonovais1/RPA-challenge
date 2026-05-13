FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="rpa-challenge" \
      org.opencontainers.image.description="RPA Challenge — Selenium + Python"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HEADLESS=1 \
    RPA_HEADLESS=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        ca-certificates \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod 0755 /docker-entrypoint.sh

COPY . .

RUN useradd --uid 1000 --create-home --shell /bin/bash appuser \
    && mkdir -p /app/database /app/logs /app/screenshots /app/output \
    && chown -R appuser:appuser /app

USER root
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "main.py"]
