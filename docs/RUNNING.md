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
- http://localhost:8000/api/ai/test
- http://localhost:8000/api/ai/board

### AI board endpoint

`POST /api/ai/board` requires auth and expects full conversation history. The response is validated, versioned, and includes a full board replacement plus an operations list.

Request body:

```json
{
	"messages": [
		{"role": "user", "content": "Move card-1 to Done"}
	]
}
```

Response body:

```json
{
	"schemaVersion": 1,
	"board": {
		"columns": [
			{"id": "col-1", "title": "Todo", "cardIds": ["card-1"]}
		],
		"cards": {
			"card-1": {"id": "card-1", "title": "Title", "details": "Details"}
		}
	},
	"operations": [
		{"type": "move_card", "cardId": "card-1", "columnId": "col-2", "position": 0}
	]
}
```
