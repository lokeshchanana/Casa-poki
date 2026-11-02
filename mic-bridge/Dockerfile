FROM python:3.11-slim

# Install system audio libraries and ALSA utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2 \
    libasound2-dev \
    libportaudio2 \
    portaudio19-dev \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bridge.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "bridge.py"]
