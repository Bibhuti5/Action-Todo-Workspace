FROM python:3.12-slim

WORKDIR /app

COPY shared/python /app/shared/python
COPY services/auth /app/services/auth

RUN pip install --no-cache-dir -r /app/services/auth/requirements.txt

ENV PYTHONPATH=/app/shared/python:/app/services/auth

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8050"]

