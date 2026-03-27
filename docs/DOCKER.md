# Docker Guide

## Build
```bash
docker build -t index-retriever:latest .
```

## Run
```bash
docker run --rm -it --env-file .env -p 8080:8080 -p 8081:8081 -p 8082:8082 -p 8083:8083 index-retriever:latest
```

## Push
```bash
docker tag index-retriever:latest registry.example.com/your-team/index-retriever:latest
docker push registry.example.com/your-team/index-retriever:latest
```

## Compose Files
- `docker-compose.yml`

## Notes
- Keep secrets out of committed compose files and environment examples.
- Use `docs/DEPLOY.md` for Vault-backed runs and custom CA certificate instructions.
