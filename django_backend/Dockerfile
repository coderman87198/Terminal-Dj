FROM python:3.12-slim

WORKDIR /app

COPY django_backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY django_backend/ .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "dj_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
