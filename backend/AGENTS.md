# Backend Overview

## Purpose

The backend provides a FastAPI service that serves static assets and exposes API endpoints. It is designed to run inside a single production-style container.

## Current Behavior

- Serves static frontend assets at / (built from the NextJS export).
- Exposes a health endpoint at /api/health.

## Structure

- app/main.py: FastAPI app, static mounting, and API routes.
- app/static/index.html: Hello world static page with a health check call.
- tests/test_health.py: Health endpoint unit test.
- requirements.txt: Backend dependencies for the container.