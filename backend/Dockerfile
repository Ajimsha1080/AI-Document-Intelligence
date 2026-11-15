FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (no external analytics/telemetry)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && tesseract --list-langs | grep -q ara || (echo "ERROR: tesseract-ocr-ara missing!" && exit 1)

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sovereign Data Guard: prevent sending traces/metrics outside UAE by default
ENV STRICT_LOCAL_ONLY=true
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
