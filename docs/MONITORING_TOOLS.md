What Runs Where:
Inside Docker Containers:
✅ Flower (Celery monitoring) - flower service in docker-compose
✅ Grafana (dashboards) - grafana service
✅ Prometheus (metrics collection) - prometheus service
✅ Redis (queue + cache) - redis service
✅ PostgreSQL (database + job history) - postgres service
✅ API (FastAPI backend) - api service
✅ Workers (Celery workers) - worker-default, worker-low services
✅ Frontend (React UI) - frontend service
✅ Exporters - redis-exporter, postgres-exporter services


On Your Local Machine:

Docker Desktop (container orchestration)
Your web browser (to access the UIs)


How It Works:
# Start everything in Docker
./start_production.sh

# Docker Compose creates 11 containers
# Each exposes ports to your localhost

Port Mapping (Docker → Localhost):

Container Port  →  Your Machine      Service
5555           →  localhost:5555    Flower UI
3001           →  localhost:3001    Grafana
9090           →  localhost:9090    Prometheus
8000           →  localhost:8000    API
3000           →  localhost:3000    Frontend
5432           →  localhost:5432    PostgreSQL
6379           →  localhost:6379    Redis

Access Pattern:

Docker runs all services in isolated containers
You open http://localhost:5555 in your browser
Docker routes the request to the Flower container
Flower responds through the exposed port

Why Docker?
✅ Consistent environment - everyone runs the same versions
✅ No local installs - don't need to install Postgres, Redis, Grafana locally
✅ Easy cleanup - docker-compose down removes everything
✅ Production-like - same setup as production deployment