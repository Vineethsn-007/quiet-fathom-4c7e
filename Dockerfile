# Backend image: FastAPI + Uvicorn serving the committed snapshot.
FROM python:3.13-slim

WORKDIR /srv

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY data data

ENV DATA_DIR=/srv/data
ENV PYTHONPATH=/srv/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
