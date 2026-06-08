FROM python:3.12-slim

WORKDIR /app

# Install dependencies from the vendored wheels (no internet access needed)
COPY requirements.txt .
COPY vendor/ vendor/
RUN pip install --no-index --find-links=vendor -r requirements.txt && rm -rf vendor/

# Copy application source
COPY app/ app/

# Run from inside the app directory so peer-level imports resolve correctly
WORKDIR /app/app

EXPOSE 5000

CMD ["python", "main.py"]
