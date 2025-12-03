# Docker Quick Start Guide

Quick reference for running the EIN Simplifier with Docker.

## Prerequisites

- Docker installed ([Install Docker](https://docs.docker.com/get-docker/))

## Quick Start

### 1. Build and Run

```bash
# Build the Docker image
make docker-build

# Start container
make docker-up

# View logs
make docker-logs
```

Or use the shell script:

```bash
./docker-run.sh build
./docker-run.sh start
./docker-run.sh logs
```

### 2. Access the Application

- Frontend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 3. Stop Container

```bash
make docker-down
# or
./docker-run.sh stop
```

## Configuration

### Environment Variables

Create a `.env` file (copy from `env.example`):

```bash
cp env.example .env
nano .env
```

Key variables:
- `CORS_ORIGINS` - Set your domain(s) for production
- `WORKERS` - Number of worker processes (default: 4)
- `LOG_LEVEL` - Logging level (info, debug, etc.)

### Data Persistence

The `storage/` and `files/` directories are mounted as volumes, so your data persists between container restarts.

## Common Commands

```bash
# Build image
make docker-build

# Start container (detached)
make docker-up

# Stop container
make docker-down

# View logs
make docker-logs

# Restart container
make docker-restart

# Open shell in container
make docker-shell

# Check status
make docker-status

# Rebuild after code changes
make docker-build && make docker-up
```

## Using the Shell Script

```bash
# Build image
./docker-run.sh build

# Start container
./docker-run.sh start

# Stop container
./docker-run.sh stop

# Restart container
./docker-run.sh restart

# View logs
./docker-run.sh logs

# Check status
./docker-run.sh status
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs ein-simplifier

# Check container status
docker ps -a | grep ein-simplifier

# Rebuild without cache
make docker-build
make docker-up
```

### Port already in use

Change the port by setting the PORT variable:

```bash
PORT=8001 make docker-up
# or edit docker-run.sh or Makefile
```

### Permission issues

```bash
# Fix permissions on mounted volumes
sudo chown -R $USER:$USER storage/ files/
```

### Data not persisting

Ensure volumes are properly mounted. Check the `docker run` command in Makefile or `docker-run.sh`:

```bash
-v "$(PWD)/storage:/app/storage"
-v "$(PWD)/files:/app/files"
```

## Production Deployment

For production deployment with Docker, see [DEPLOYMENT.md](./DEPLOYMENT.md#docker-deployment-recommended).

Key production considerations:
1. Set `CORS_ORIGINS` to your actual domain
2. Use Nginx reverse proxy on the host (see DEPLOYMENT.md)
3. Set up SSL certificates
4. Configure proper firewall rules
5. Set up regular backups

## Development with Docker

For development, you can mount the code as a volume for live reloading. Edit the `docker-up` target in Makefile or `docker-run.sh` to add:

```bash
-v "$(PWD)/main.py:/app/main.py"
-v "$(PWD)/index.html:/app/index.html"
```

Then set `RELOAD=true` in your `.env` file.

## Image Details

- **Base Image**: `python:3.11-slim`
- **Port**: 8000
- **User**: Non-root user (`appuser`) for security
- **Health Check**: Built-in health check endpoint
- **Workers**: 4 (configurable via environment)

## Building for Different Platforms

```bash
# Build for specific platform
docker buildx build --platform linux/amd64 -t ein-simplifier .

# Build for ARM (e.g., Raspberry Pi)
docker buildx build --platform linux/arm64 -t ein-simplifier .
```

