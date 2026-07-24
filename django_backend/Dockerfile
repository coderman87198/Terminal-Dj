FROM python:3.12-slim

# Install ffmpeg for pydub audio processing
RUN apt-get update && apt-get install -y ffmpeg nodejs && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY django_backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY django_backend/ .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "dj_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
