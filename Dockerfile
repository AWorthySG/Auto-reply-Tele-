FROM python:3.12-slim

WORKDIR /app

# Mutable runtime data (session + state) lives here; mount a volume at /data.
# Config is read from /app/config.yaml (mount it read-only).
ENV SESSION_NAME=/data/autoreply \
    STATE_PATH=/data/state.json \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY autoreply/ ./autoreply/
COPY login.py ./

# Run as a non-root user; /data is created and owned by it.
RUN useradd --create-home --uid 10001 autoreply \
    && mkdir -p /data \
    && chown -R autoreply:autoreply /data
USER autoreply

# Use CMD (not ENTRYPOINT) so `docker run ... python login.py` is easy.
CMD ["python", "-m", "autoreply.main"]
