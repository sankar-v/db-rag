#!/bin/bash
cd /Users/ananth1/Documents/projects/db-rag/backend
exec ./venv/bin/uvicorn api:app --reload --host 0.0.0.0 --port 8000
