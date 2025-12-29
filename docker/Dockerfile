FROM postgres:16

# Install pgvector extension and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-16-pgvector \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download Pagila database files
RUN mkdir -p /tmp/pagila && \
    cd /tmp/pagila && \
    curl -L https://raw.githubusercontent.com/devrimgunduz/pagila/master/pagila-schema.sql -o pagila-schema.sql && \
    curl -L https://raw.githubusercontent.com/devrimgunduz/pagila/master/pagila-data.sql -o pagila-data.sql

# Set environment variables
ENV POSTGRES_DB=pagila
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

# Create directory for initialization scripts
RUN mkdir -p /docker-entrypoint-initdb.d

# Copy initialization scripts
COPY init-scripts/ /docker-entrypoint-initdb.d/

EXPOSE 5432
