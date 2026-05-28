FROM python:3.12-slim

WORKDIR /app

COPY shared/python /app/shared/python
COPY services/ingestion /app/services/ingestion

RUN pip install --no-cache-dir -r /app/services/ingestion/requirements.txt

ENV PYTHONPATH=/app/shared/python:/app/services/ingestion

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]

