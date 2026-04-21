FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables (should be provided by the host)
ENV PORT=8080

EXPOSE 8080

CMD ["python", "main.py"]
