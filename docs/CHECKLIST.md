# 🚀 DB-RAG Setup Checklist

## ✅ Pre-Launch Checklist

Before running the application, verify:

### 1. Prerequisites Installed
- [ ] Docker Desktop installed and running
- [ ] Docker Compose available (`docker-compose --version`)
- [ ] Git installed (if cloning)
- [ ] Text editor (VS Code recommended)

### 2. Environment Configuration
- [ ] `.env` file created (copy from `.env.example`)
- [ ] `OPENAI_API_KEY` set in `.env` file
- [ ] API key starts with `sk-` and is valid
- [ ] No other PostgreSQL running on port 5433

### 3. File Structure Verification

**Backend Files:**
- [ ] `backend/api.py` - REST API endpoints
- [ ] `backend/main.py` - Main DBRAG class
- [ ] `backend/orchestrator.py` - Query router
- [ ] `backend/sql_agent.py` - SQL generator
- [ ] `backend/vector_agent.py` - Vector search
- [ ] `backend/metadata_catalog.py` - Table discovery
- [ ] `backend/database.py` - DB manager
- [ ] `backend/config.py` - Configuration
- [ ] `backend/requirements.txt` - Dependencies
- [ ] `backend/Dockerfile` - Container config

**Frontend Files:**
- [ ] `frontend/package.json` - Dependencies
- [ ] `frontend/src/App.tsx` - Main app
- [ ] `frontend/src/main.tsx` - Entry point
- [ ] `frontend/src/pages/ChatInterface.tsx`
- [ ] `frontend/src/pages/DocumentManager.tsx`
- [ ] `frontend/src/pages/DatabaseConnections.tsx`
- [ ] `frontend/src/pages/MetadataExplorer.tsx`
- [ ] `frontend/src/components/Layout.tsx`
- [ ] `frontend/src/api/client.ts` - API client
- [ ] `frontend/Dockerfile` - Container config

**Docker Files:**
- [ ] `docker-compose.yml` - Multi-container setup
- [ ] `docker/Dockerfile` - PostgreSQL image
- [ ] `docker/init-scripts/` - DB initialization

**Scripts & Docs:**
- [ ] `start.sh` - Automated setup (executable)
- [ ] `README.md` - Main documentation
- [ ] `PROJECT_SUMMARY.md` - Project overview
- [ ] `DEVELOPMENT.md` - Dev guide

## 🎯 Startup Steps

### Option 1: Automated Setup (Recommended)
```bash
# Make script executable
chmod +x start.sh

# Run setup
./start.sh
```

The script will:
1. ✅ Verify Docker is running
2. ✅ Check environment configuration
3. ✅ Build all containers
4. ✅ Start services
5. ✅ Wait for health checks
6. ✅ Display access URLs

### Option 2: Manual Setup
```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## 🧪 Post-Startup Verification

### 1. Check Services Running
```bash
docker-compose ps
```

Expected output:
```
NAME                STATUS              PORTS
dbrag-postgres     Up (healthy)        0.0.0.0:5433->5432/tcp
dbrag-backend      Up                  0.0.0.0:8000->8000/tcp
dbrag-frontend     Up                  0.0.0.0:3000->3000/tcp
```

### 2. Verify PostgreSQL
```bash
docker exec -it dbrag-postgres psql -U postgres -d pagila -c "SELECT COUNT(*) FROM film;"
```

Should return: `1000`

### 3. Test Backend API
```bash
curl http://localhost:8000/health
```

Should return: `{"status":"healthy","service":"db-rag-api"}`

### 4. Test Backend Status
```bash
curl http://localhost:8000/api/status
```

Should return status JSON with `database_connected: true`

### 5. Access Frontend
Open browser to: http://localhost:3000

Should see the DB-RAG interface with:
- ✅ Chat interface loads
- ✅ Navigation menu visible
- ✅ Status shows "Connected"
- ✅ No console errors

### 6. Test Sample Query

In the chat interface, try:
```
How many customers do we have?
```

Expected:
- ✅ Query sends successfully
- ✅ Response received within 5-10 seconds
- ✅ Answer shows "599 customers"
- ✅ No errors in browser console

## 🎮 First-Time Usage Guide

### 1. Explore the Chat Interface (Main Feature)
1. Go to http://localhost:3000/chat
2. Try these sample queries:
   - "How many customers do we have?"
   - "What are the top 5 most rented films?"
   - "Show me rentals from last week"
3. Verify responses are accurate
4. Check query routing in response metadata

### 2. Upload Your First Document
1. Go to Documents page
2. Click "Add Text" tab
3. Paste this sample:
   ```
   Company Policy: All employees are entitled to 15 days of paid vacation per year.
   Vacation days must be requested at least 2 weeks in advance.
   ```
4. Click "Add Document"
5. Wait for "Document added successfully"
6. Go back to Chat
7. Ask: "What is the vacation policy?"
8. Verify it returns the policy information

### 3. Explore Metadata
1. Go to Metadata page
2. See all 22 Pagila tables
3. Click on "film" table
4. Review:
   - AI-generated description
   - Column list
   - Sample data
5. Click "Sync Metadata" to refresh

### 4. Configure Database (Optional)
1. Go to Connections page
2. Default settings are already correct:
   - Host: localhost
   - Port: 5433
   - Database: pagila
   - User: postgres
   - Password: postgres
3. Click "Test Connection"
4. Should show "Connection successful"

## 🐛 Troubleshooting

### Backend Won't Start

**Symptom**: `docker-compose logs backend` shows errors

**Check:**
1. OpenAI API key is set correctly
   ```bash
   grep OPENAI_API_KEY .env
   ```
2. PostgreSQL is healthy
   ```bash
   docker-compose ps postgres
   ```
3. View detailed logs
   ```bash
   docker-compose logs -f backend
   ```

**Solution**: Most issues are due to missing or invalid OpenAI API key

### Frontend Shows "Disconnected"

**Symptom**: Status indicator is red, shows "Disconnected"

**Check:**
1. Backend is running
   ```bash
   curl http://localhost:8000/health
   ```
2. Check frontend console (F12)
3. View network tab for failed requests

**Solution**: Ensure backend is started and healthy

### PostgreSQL Not Starting

**Symptom**: `dbrag-postgres` container exiting

**Check:**
1. Port 5433 is available
   ```bash
   lsof -i :5433
   ```
2. View PostgreSQL logs
   ```bash
   docker-compose logs postgres
   ```

**Solution**: Stop other PostgreSQL instances or change port

### Port Already in Use

**Symptom**: "port is already allocated" error

**Solution:**
1. Find what's using the port
   ```bash
   lsof -i :3000  # or :8000 or :5433
   ```
2. Stop the conflicting service
3. Or change port in `docker-compose.yml`

### Can't Connect to Database

**Symptom**: "Database not connected" in UI

**Check:**
1. PostgreSQL is running
   ```bash
   docker exec dbrag-postgres pg_isready -U postgres
   ```
2. Backend can connect
   ```bash
   docker-compose logs backend | grep -i database
   ```

**Solution**: Verify credentials in Connections page

## 📊 Health Dashboard

Use this quick reference to check system health:

```bash
# All services status
docker-compose ps

# PostgreSQL health
docker exec dbrag-postgres pg_isready -U postgres -d pagila

# Backend health
curl http://localhost:8000/health

# System status (detailed)
curl http://localhost:8000/api/status | jq

# View real-time logs
docker-compose logs -f

# Resource usage
docker stats dbrag-postgres dbrag-backend dbrag-frontend
```

## 🎯 Success Criteria

Your system is fully operational when:

- [ ] All 3 Docker containers running
- [ ] PostgreSQL responds to queries
- [ ] Backend API health check passes
- [ ] Frontend loads without errors
- [ ] Status shows "Connected"
- [ ] Sample SQL query returns results
- [ ] Document upload works
- [ ] Metadata sync completes
- [ ] No errors in logs

## 📞 Getting Help

If you encounter issues:

1. **Check logs**: `docker-compose logs -f`
2. **Review documentation**: `README.md`, `DEVELOPMENT.md`
3. **API docs**: http://localhost:8000/docs
4. **System status**: http://localhost:8000/api/status
5. **Restart services**: `docker-compose restart`
6. **Rebuild**: `docker-compose up --build`
7. **Clean start**: `docker-compose down -v && docker-compose up --build`

## 🎊 You're All Set!

If all checks pass, you have:
- ✅ A fully functional Agentic RAG system
- ✅ Natural language to SQL capability
- ✅ Semantic document search
- ✅ Modern web interface
- ✅ Complete Docker environment
- ✅ Sample database loaded

**Start asking questions and exploring your data!** 🚀

Go to: http://localhost:3000
