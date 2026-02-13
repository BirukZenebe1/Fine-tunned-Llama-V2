FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for bcrypt build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Use lightweight deploy requirements (no training packages)
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt \
    && rm -rf /root/.cache/pip

# Copy application code
COPY app.py auth.py memory.py ./

# Create data directory for persistent storage
RUN mkdir -p data/history

# Expose Gradio default port
EXPOSE 7860

# Support PORT env variable (Render, Railway) with fallback to 7860
ENV GRADIO_SERVER_NAME=0.0.0.0
CMD ["python", "app.py", "--cpu", "--port", "7860"]
