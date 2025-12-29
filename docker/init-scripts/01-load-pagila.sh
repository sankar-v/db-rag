#!/bin/bash
set -e

echo "========================================"
echo "Initializing Pagila Sample Database"
echo "========================================"

# Pagila files are already downloaded during Docker build
cd /tmp/pagila

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

echo "Pagila database loaded successfully!"
