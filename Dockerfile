# ME-1 Config Editor
# Multi-platform build — supports linux/amd64, linux/arm64, linux/arm/v7
FROM python:3.11-slim

# Metadata
LABEL org.opencontainers.image.title="ME-OLE — ME Offline Editor"
LABEL org.opencontainers.image.description="ME-OLE: Offline editor for Allen & Heath ME-1 config files"
LABEL org.opencontainers.image.version="0.93"
LABEL org.opencontainers.image.source="https://hub.docker.com"

# Don't write .pyc files, don't buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Install dependencies (cached layer — only reruns when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY me1.py .
COPY me1_editor.py .

# Non-root user for security
RUN useradd --no-create-home --shell /bin/false appuser

# Create the configs volume directory with correct ownership before dropping to non-root
RUN mkdir -p /data/configs && chown -R appuser:appuser /data

USER appuser

VOLUME ["/data/configs"]
EXPOSE 5000

# Gunicorn: production WSGI server
#   --bind 0.0.0.0        accept connections from any host (required in Docker)
#   --workers 1           single worker — app is stateful (in-memory config)
#   --threads 2           handle concurrent requests within that worker
#   --timeout 120         allow up to 120s for large file uploads/downloads
CMD ["gunicorn", "me1_editor:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
