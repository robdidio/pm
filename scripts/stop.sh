#!/usr/bin/env bash
set -euo pipefail

docker stop pm-app
docker rm pm-app
