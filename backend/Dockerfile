FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY frontend/dist/ ./frontend_dist/

# SQLite DB lives on a persistent Fly.io volume
ENV DATABASE_URL=sqlite:////data/student.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
