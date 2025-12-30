#!/bin/bash
set -e

echo "========================================"
echo "Initializing Data Plane Databases"
echo "========================================"

# Create Pagila database
echo "Creating Pagila database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE pagila;
EOSQL

echo "Loading Pagila schema and data..."
cd /tmp/pagila
psql -U "$POSTGRES_USER" -d pagila -f pagila-schema.sql
psql -U "$POSTGRES_USER" -d pagila -f pagila-data.sql

echo "✅ Pagila database loaded successfully!"
echo "   - 31 tables with DVD rental data"

# Create AdventureWorks database
echo ""
echo "Creating AdventureWorks database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE adventureworks;
EOSQL

echo "Loading AdventureWorks schema and data..."
cd /tmp/adventureworks
psql -U "$POSTGRES_USER" -d adventureworks -f install.sql

echo "✅ AdventureWorks database loaded successfully!"
echo "   - Business database with Sales, HR, Production schemas"

echo ""
echo "========================================"
echo "Data Plane Initialization Complete!"
echo "Available databases:"
echo "  - pagila (port 5435)"
echo "  - adventureworks (port 5435)"
echo "========================================"
