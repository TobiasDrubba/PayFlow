# 1️⃣ Use an official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY ./app ./app
COPY ./resources ./resources
COPY .env /.env

# Expose FastAPI default port
EXPOSE 8000

# Use uvicorn as the ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
