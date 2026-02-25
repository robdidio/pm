#!/usr/bin/env bash
set -euo pipefail

docker build -t pm-app .
docker run -d --name pm-app -p 8000:8000 --env-file .env pm-app

echo "Running at http://localhost:8000"
