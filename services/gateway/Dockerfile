FROM python:3.12-slim

WORKDIR /app

COPY shared/python /app/shared/python
COPY services/gateway /app/services/gateway

RUN pip install --no-cache-dir -r /app/services/gateway/requirements.txt

ENV PYTHONPATH=/app/shared/python:/app/services/gateway

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

