FROM python:3.12-slim

WORKDIR /app

COPY processor/requirements.txt /app/processor/
RUN pip install --no-cache-dir -r processor/requirements.txt

COPY config/ /app/config/
COPY storage/ /app/storage/
COPY processor/ /app/processor/

CMD ["python", "-m", "processor.main"]
