# Running the container

## Start

- Windows: scripts/start.ps1
- macOS/Linux: scripts/start.sh

## Stop

- Windows: scripts/stop.ps1
- macOS/Linux: scripts/stop.sh

## Manual commands

```bash
docker build -t pm-app .
docker run -d --name pm-app -p 8000:8000 --env-file .env pm-app
```

The container build runs the NextJS static export and serves it from FastAPI.

```bash
docker stop pm-app
docker rm pm-app
```

## Endpoints

- http://localhost:8000/
- http://localhost:8000/api/health
