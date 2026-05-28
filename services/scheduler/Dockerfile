FROM python:3.12-slim

WORKDIR /app

COPY shared/python /app/shared/python
COPY services/scheduler /app/services/scheduler

RUN pip install --no-cache-dir -r /app/services/scheduler/requirements.txt

ENV PYTHONPATH=/app/shared/python:/app/services/scheduler

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]

