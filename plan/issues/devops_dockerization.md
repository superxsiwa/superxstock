# Issue: Dockerize Backend Application (Cloud Deployment Preparation)

**Label:** `devops`, `deployment`
**Status:** `To Do`
**Assignee:** DevOps Team

## Description
The application needs to be packaged in Docker containers so we can deploy it easily to a cloud provider in Phase 6. While we already use `docker-compose.yml` for TimescaleDB and Redis, the FastAPI backend and Celery workers are currently running on bare metal/virtual environments locally.

## Acceptance Criteria
- [ ] Create a `Dockerfile` for the Python backend in the `backend/` directory.
- [ ] Update `docker-compose.yml` to include two new services: `api` (FastAPI) and `worker` (Celery).
- [ ] The `api` service should build from the `Dockerfile` and expose port `8000`.
- [ ] Ensure that both `api` and `worker` wait for `db` (TimescaleDB) and `redis` to be healthy before starting.
- [ ] Use environment variables in `docker-compose.yml` for DB connection strings and Redis URLs.

## Technical Details
- Base Image: `python:3.11-slim` or newer.
- Requirements: Copy `backend/requirements.txt` and install before copying the source code for layer caching.
- Start command for API: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Start command for Worker: `celery -A app.worker.celery_app worker --loglevel=info` and `celery -A app.worker.celery_app beat`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     