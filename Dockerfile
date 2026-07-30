FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data
RUN mkdir -p /app/jsons

EXPOSE 8000

ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/data/db.sqlite3

CMD ["python", "munbabb/manage.py", "runserver", "0.0.0.0:8000"]
