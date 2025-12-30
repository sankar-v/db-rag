#!/bin/bash
set -e

echo "========================================"
echo "Initializing AdventureWorks Database"
echo "========================================"

# Download AdventureWorks for PostgreSQL using wget
ADVENTUREWORKS_DIR="/tmp/adventureworks"
mkdir -p "$ADVENTUREWORKS_DIR"
cd "$ADVENTUREWORKS_DIR"

echo "Downloading AdventureWorks database..."
wget -q -O adventureworks.tar.gz https://github.com/lorint/AdventureWorks-for-Postgres/archive/master.tar.gz
tar -xzf adventureworks.tar.gz --strip-components=1

# The repository has install.sql which orchestrates the installation
if [ ! -f "install.sql" ]; then
    echo "ERROR: AdventureWorks install.sql not found!"
    exit 1
fi

echo "Creating AdventureWorks schema and loading data..."
psql -U postgres -d adventureworks -f install.sql

echo "✅ AdventureWorks database loaded successfully!"
echo "   - Business sample database with sales, HR, production data"
echo "   - Multiple schemas: Sales, HumanResources, Production, Purchasing"
