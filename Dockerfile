# Use AMD64 compatible Python base image
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Make the main script executable
RUN chmod +x src/pdf_outline_extractor.py

# Set the default command to process all PDFs in input directory
CMD ["python", "src/pdf_outline_extractor.py", "--input", "/app/input", "--output", "/app/output"]
