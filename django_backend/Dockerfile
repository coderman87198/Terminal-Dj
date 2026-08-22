FROM python:3.12-slim

# Install ffmpeg for pydub audio processing and nodejs for yt-dlp JS runtime if needed
RUN apt-get update && apt-get install -y ffmpeg nodejs && rm -rf /var/lib/apt/lists/*

ENV YT_DLP_JS_RUNTIME=node

WORKDIR /app

COPY django_backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code and entrypoint script
COPY django_backend/ .
COPY django_backend/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh
RUN python manage.py collectstatic --noinput

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "dj_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
