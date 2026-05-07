FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker
RUN pip install --no-cache-dir -e /app/apps/api

WORKDIR /app/apps/worker

CMD ["python", "-m", "app.worker"]
