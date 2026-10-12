FROM python:3.12-slim

RUN groupadd -g 1001 appuser && useradd -u 1001 -g appuser -m -s /bin/bash appuser

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app
ENV PORT=8000
ENV HOST=0.0.0.0

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
