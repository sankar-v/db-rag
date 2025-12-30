#!/bin/bash
set -e

echo "========================================"
echo "Initializing Pagila Sample Database"
echo "========================================"

# Download Pagila database using wget (available in postgres container)
PAGILA_DIR="/tmp/pagila"
mkdir -p "$PAGILA_DIR"
cd "$PAGILA_DIR"

echo "Downloading Pagila database..."
wget -q -O pagila.tar.gz https://github.com/devrimgunduz/pagila/archive/master.tar.gz
tar -xzf pagila.tar.gz --strip-components=1

if [ ! -f "pagila-schema.sql" ]; then
    echo "ERROR: Pagila schema file not found!"
    exit 1
fi

if [ ! -f "pagila-data.sql" ]; then
    echo "ERROR: Pagila data file not found!"
    exit 1
fi

echo "Creating Pagila schema..."
psql -U postgres -d pagila -f pagila-schema.sql

echo "Loading Pagila data..."
psql -U postgres -d pagila -f pagila-data.sql

echo "✅ Pagila database loaded successfully!"
echo "   - 31 tables loaded"
echo "   - Sample DVD rental data available"
