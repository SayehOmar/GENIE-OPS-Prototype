# Backend Server Startup Guide

## Quick Start

### Option 1: Use the Batch File (Recommended)
Run `start-dev.bat` from the project root. This will start both backend and frontend servers.

### Option 2: Manual Start

#### 1. Start Backend Server

Open a terminal in the `backend` directory:

```bash
cd backend

# Activate virtual environment
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Start the server
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### 2. Verify Backend is Running

Open your browser and visit:
- **API Root**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Database Connection Issues

If the backend fails to start due to database connection errors:

### 1. Check PostgreSQL is Running

**Windows:**
- Open Services (`services.msc`)
- Look for "postgresql-x64-XX" service
- Ensure it's running

**Or check via command:**
```bash
# Check if PostgreSQL is listening on port 5432
netstat -an | findstr 5432
```

### 2. Verify Database Exists

Connect to PostgreSQL and create the database if it doesn't exist:

```sql
-- Connect to PostgreSQL (using psql or pgAdmin)
CREATE DATABASE genie_ops;

-- Then run the schema file
-- File location: backend/storage/schema.sql
```

### 3. Check Database Connection String

The default connection string is in `backend/app/core/config.py`:
```python
DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/genie_ops"
```

**Format:** `postgresql://username:password@host:port/database_name`

**To customize**, create a `.env` file in the `backend` directory:
```env
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/genie_ops
```

### 4. Common Database Errors

**Error: "connection refused"**
- PostgreSQL is not running
- Wrong port (default is 5432)

**Error: "database does not exist"**
- Create the database: `CREATE DATABASE genie_ops;`
- Run the schema: `backend/storage/schema.sql`

**Error: "password authentication failed"**
- Check username/password in connection string
- Verify PostgreSQL user credentials

**Error: "relation does not exist"**
- Database exists but tables are missing
- Run the schema file: `backend/storage/schema.sql`

## Troubleshooting

### Backend Server Won't Start

1. **Check Python version**: Requires Python 3.8+
   ```bash
   python --version
   ```

2. **Check dependencies**: Install requirements
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Check virtual environment**: Ensure venv is activated
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

4. **Check port 8000**: Ensure no other service is using it
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```

### Database Connection Fails

1. **Test PostgreSQL connection directly:**
   ```bash
   psql -U postgres -h localhost -p 5432
   ```

2. **Check PostgreSQL logs** for detailed error messages

3. **Verify firewall** isn't blocking port 5432

4. **Check connection string** matches your PostgreSQL setup

## Next Steps

Once the backend is running:
1. Verify it's accessible at http://localhost:8000
2. Check API docs at http://localhost:8000/docs
3. Start the frontend server (if not already running)
4. Test the form submission from the frontend
