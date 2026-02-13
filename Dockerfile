FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py auth.py memory.py ./

# Create data directory for persistent storage
RUN mkdir -p data/history

# Expose Gradio default port
EXPOSE 7860

# Run the application (CPU mode for free-tier)
CMD ["python", "app.py", "--cpu", "--port", "7860"]
