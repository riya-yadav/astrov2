FROM python:3.10-slim

# Install system dependencies for pyswisseph
RUN apt-get update && apt-get install -y build-essential

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port
EXPOSE 8080

# Start the server
CMD ["python", "main.py"]