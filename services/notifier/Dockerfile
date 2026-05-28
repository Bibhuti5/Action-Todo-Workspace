FROM python:3.12-slim

WORKDIR /app

COPY shared/python /app/shared/python
COPY services/notifier /app/services/notifier

RUN pip install --no-cache-dir -r /app/services/notifier/requirements.txt

ENV PYTHONPATH=/app/shared/python:/app/services/notifier

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8040"]

