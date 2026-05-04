FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg libsndfile1 libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p assets/videos assets/audio outputs/scripts outputs/analysis outputs/reports

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
