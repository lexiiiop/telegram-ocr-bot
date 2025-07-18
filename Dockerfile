# Use official Python image
FROM python:3.12-slim

# Install Tesseract and language packs, and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-ita \
    tesseract-ocr-por tesseract-ocr-rus tesseract-ocr-jpn tesseract-ocr-chi-sim tesseract-ocr-ara \
    tesseract-ocr-tur tesseract-ocr-nld tesseract-ocr-pol tesseract-ocr-ces tesseract-ocr-ell \
    tesseract-ocr-kor tesseract-ocr-ukr tesseract-ocr-ron tesseract-ocr-swe \
    libglib2.0-0 libsm6 libxrender1 libxext6 gcc build-essential \
    neofetch \
    && \
    rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port (if needed, for Railway health checks)
EXPOSE 8080

# Run the bot
CMD ["python", "main.py"] 