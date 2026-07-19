FROM python:3.11-slim

WORKDIR /app

# Install system dependencies.
# freetds-dev/-bin let pymssql (MSSQL) build/run if no binary wheel is available.
# oracledb runs in thin mode, so no Oracle Instant Client is needed.
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    freetds-dev \
    freetds-bin \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY tools.py .
COPY server.py .

# Make server executable
RUN chmod +x server.py

# Set environment variables
ENV HTTP_HOST=0.0.0.0 \
    HTTP_PORT=3001

# Expose port
EXPOSE 3001

# Run the server with uvicorn
CMD ["python", "server.py"]
