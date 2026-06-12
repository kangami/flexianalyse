FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY tools.py .
COPY server.py .

# Create secrets directory
RUN mkdir -p /secrets

# Make server executable
RUN chmod +x server.py

# Set environment variables
ENV HTTP_HOST=0.0.0.0 \
    HTTP_PORT=3002

# Expose port
EXPOSE 3002

# Run the server with uvicorn
CMD ["python", "server.py"]
