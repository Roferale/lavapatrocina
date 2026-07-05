FROM python:3.11-slim

# ── System libraries required by OpenCV and general networking ──────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ──────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Pre-download the YOLO model so the container starts fast ─────────────────
# YOLO_MODEL can be overridden at runtime; we bake in the default.
ARG YOLO_MODEL=yolo11n.pt
RUN python -c "from ultralytics import YOLO; YOLO('${YOLO_MODEL}')"

# ── Application code ─────────────────────────────────────────────────────────
COPY . .

# Snapshot storage (mounted as a volume in docker-compose)
RUN mkdir -p /app/snapshots

# ── Runtime ─────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "worker.main"]
