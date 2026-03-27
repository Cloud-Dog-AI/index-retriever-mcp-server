# API Documentation

## Base URLs
- Local development: `http://localhost:8083`
- Deployed: `https://index-retriever.your-domain.com`

## Authentication
Use `Authorization: Bearer <your-api-key>` or `X-API-Key: <your-api-key>`; administrative tools require an admin-capable role.

## Verification Basis
- Source files reviewed: `src/index_server/a2a_server.py`, `src/index_server/api_server.py`, `src/index_server/mcp_server.py`, `src/index_server/web_server.py`
- Route inventory size: 3

## Route Inventory
| Method | Path | Notes |
|--------|------|-------|
| POST | `/auth/login` | Handler `auth_login` in `src/index_server/api_server.py`. |
| GET | `/auth/me` | Handler `auth_me` in `src/index_server/api_server.py`. |
| POST | `/auth/logout` | Handler `auth_logout` in `src/index_server/api_server.py`. |

## Example Request
```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8083/health
```

## Example Response
```json
{
  "ok": true,
  "result": {
    "status": "healthy"
  }
}
```
