FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json /frontend/package.json
RUN npm install --no-audit --no-fund

COPY frontend /frontend
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

COPY backend/requirements.txt /app/requirements.txt
RUN uv pip install --system --no-cache -r /app/requirements.txt

COPY backend/app /app/app
COPY --from=frontend-builder /frontend/out /app/app/static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
