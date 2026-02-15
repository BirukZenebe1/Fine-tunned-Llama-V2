FROM python:3.12-slim

WORKDIR /app

COPY producers/requirements.txt /app/producers/
RUN pip install --no-cache-dir -r producers/requirements.txt

COPY config/ /app/config/
COPY producers/ /app/producers/

CMD ["python", "-m", "producers.iot_producer"]
