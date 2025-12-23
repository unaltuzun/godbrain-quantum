FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir flask flask-cors redis

COPY mobile_api.py .
COPY config_center.py .
COPY .env .

EXPOSE 8001

CMD ["python", "mobile_api.py"]
