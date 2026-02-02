# Dockerfile for 3D volumetric pipeline (CPU)
FROM python:3.11-slim

WORKDIR /app

# Install system deps (including ExifTool for HEIC/JPEG metadata)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 gcc libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
