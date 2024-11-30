FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --timeout=120 -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["watchmedo", "auto-restart", "--recursive", "--", "python", "main.py"]
