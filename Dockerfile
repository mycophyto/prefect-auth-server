FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Set environment variables
ENV PYTHONPATH=/app
ENV PREFECT_SERVER_API_HOST=0.0.0.0
ENV PREFECT_SERVER_API_PORT=4200

# Expose the port
EXPOSE 4200

# Run the application
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "4200", "--factory", "app.server:create_auth_app"]
