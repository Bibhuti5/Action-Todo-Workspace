FROM python:3.12-slim

WORKDIR /app

COPY shared/python /app/shared/python
COPY services/summarizer /app/services/summarizer

RUN pip install --no-cache-dir -r /app/services/summarizer/requirements.txt

ENV PYTHONPATH=/app/shared/python:/app/services/summarizer

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8030"]

