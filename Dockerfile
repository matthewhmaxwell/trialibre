# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim AS runtime
WORKDIR /app

# System deps for Tesseract OCR and WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-por tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-ara \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python package
COPY backend/ ./backend/
RUN pip install --no-cache-dir ./backend

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Config
ENV TRIALIBRE_FRONTEND_DIR=/app/frontend/dist
ENV TRIALIBRE_DATA_DIR=/data
VOLUME /data

EXPOSE 8000

CMD ["trialibre", "serve", "--host", "0.0.0.0", "--port", "8000"]
