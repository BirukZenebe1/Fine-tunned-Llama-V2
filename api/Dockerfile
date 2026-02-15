FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt /app/api/
RUN pip install --no-cache-dir -r api/requirements.txt

COPY config/ /app/config/
COPY storage/ /app/storage/
COPY api/ /app/api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
