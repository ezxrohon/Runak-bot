# Only needed because of the music feature (handlers/music.py), which
# requires the `ffmpeg` binary - Render's default Python runtime doesn't
# include it, so this Dockerfile is what gets you there. If you never
# set SESSION_STRING (music stays disabled), you can keep deploying
# without Docker and delete this file - it changes nothing else.

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "main.py"]
