# AdventureWorks Database Dockerfile
FROM pgvector/pgvector:pg16

# Install wget for downloading init scripts
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

COPY 01-load-adventureworks.sh /docker-entrypoint-initdb.d/
RUN chmod +x /docker-entrypoint-initdb.d/01-load-adventureworks.sh
