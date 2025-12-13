FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Supervisor config
COPY deploy/gcloud/supervisord.conf /etc/supervisor/conf.d/godbrain.conf

# Expose Redis port
EXPOSE 6379

# Start supervisor
CMD ["/usr/bin/supervisord", "-n"]
