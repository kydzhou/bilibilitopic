FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    BASE_PATH=/btopic

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyzer ./analyzer
COPY web ./web
COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "web.app:application", "--host", "0.0.0.0", "--port", "8000"]
