# GENIE-OPS - Automated SaaS Directory Submission Agent

**Automated SaaS directory submission system that submits your SaaS to hundreds of directories without manual work.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://reactjs.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40.0-45ba4b?logo=playwright)](https://playwright.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-336791?logo=postgresql)](https://www.postgresql.org/)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

GENIE-OPS is an intelligent automation system that streamlines the process of submitting SaaS products to multiple directories. Instead of manually filling out forms across hundreds of directories, GENIE-OPS:

1. **Opens directory websites** automatically
2. **Detects and analyzes submission forms** using AI
3. **Fills forms** with your SaaS information
4. **Submits listings** and tracks their status
5. **Monitors progress** in real-time via a dashboard

**Result:** Save dozens of hours and scale your distribution efforts.

---

## 🏗️ Architecture

GENIE-OPS follows a **3-layer architecture** that separates concerns and ensures scalability:

### Architecture Diagram

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React Dashboard]
        UI -->|HTTP/REST| API[FastAPI Backend]
    end
    
    subgraph "Backend Layer - Control Center"
        API -->|Manages| WM[Workflow Manager]
        WM -->|Queues| DB[(PostgreSQL)]
        WM -->|Orchestrates| WF[Submission Workflow]
    end
    
    subgraph "Brain Layer - AI Form Reader"
        WF -->|Extracts HTML| BR[Form Reader]
        BR -->|Analyzes| LLM[Ollama LLM]
        LLM -->|Returns Structure| BR
        BR -->|DOM Fallback| DOM[DOM Parser]
    end
    
    subgraph "Hands Layer - Browser Automation"
        WF -->|Commands| BP[Browser Pool]
        BP -->|Process Isolation| BW[Browser Workers]
        BW -->|Playwright| CHR[Chromium Browser]
        CHR -->|Interacts| WEB[Directory Websites]
    end
    
    subgraph "Data Layer"
        DB -->|Stores| SAAS[SaaS Products]
        DB -->|Tracks| SUB[Submissions]
        DB -->|Lists| DIR[Directories]
    end
    
    style UI fill:#61DAFB
    style API fill:#009688
    style WM fill:#FF6B6B
    style BR fill:#4ECDC4
    style BP fill:#45BA4B
    style DB fill:#336791
```

### Layer Breakdown

#### 1. **Brain Layer (AI Form Reader)**
- **Purpose:** Understand page layout and detect form fields
- **Technology:** Ollama LLM (local) with OpenAI-compatible API
- **Fallback:** DOM-based extraction for reliability
- **Key Features:**
  - Intelligent field detection (name, URL, email, description, category, logo)
  - Field mapping and validation
  - Handles dynamic forms and JavaScript-rendered content

#### 2. **Hands Layer (Browser Automation)**
- **Purpose:** Actually click, type, and interact with web pages
- **Technology:** Playwright with process isolation
- **Key Features:**
  - Windows-compatible worker pool (process isolation)
  - Session-based browser reuse (one browser per workflow)
  - Robust form filling with value verification
  - Multiple submit strategies (normal, force, JavaScript)
  - CAPTCHA detection
  - Screenshot capture for debugging

#### 3. **Control Center (Workflow Manager)**
- **Purpose:** Run submissions at scale with queue management
- **Technology:** AsyncIO-based task scheduling
- **Key Features:**
  - Automatic batch processing
  - Retry logic with exponential backoff
  - Real-time progress tracking
  - Status management (pending → submitted/approved/failed)
  - Rate limiting and duplicate prevention

---

## ✨ Features

### Core Functionality
- ✅ **Automated Form Detection:** AI-powered form field detection with DOM fallback
- ✅ **Intelligent Field Mapping:** Maps SaaS data to detected form fields
- ✅ **Multi-Directory Support:** Submit to multiple directories in parallel
- ✅ **Real-Time Dashboard:** Track submissions, success rates, and progress
- ✅ **Retry Logic:** Automatic retry for failed submissions (max 3 attempts)
- ✅ **Status Tracking:** Pending → Submitted → Approved/Failed

### Advanced Features
- ✅ **Windows Threading Solution:** Process isolation for Playwright on Windows
- ✅ **Session-Based Workers:** One browser instance per workflow
- ✅ **Colored Logging:** Visual log messages with color-coded status
- ✅ **Rate Limiting:** API rate limits to prevent abuse
- ✅ **CAPTCHA Detection:** Automatically detects and handles CAPTCHA
- ✅ **Progress Tracking:** Real-time progress bars and status updates
- ✅ **Error Handling:** Comprehensive error messages and debugging info

### Safety Features
- ✅ **Duplicate Prevention:** Skips already-submitted directories
- ✅ **Timeout Limits:** Prevents hanging on slow sites
- ✅ **Validation:** Form validation before submission
- ✅ **Rate Limiting:** API and workflow rate limits

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI 0.104.1
- **Database:** PostgreSQL (with SQLAlchemy ORM)
- **Automation:** Playwright 1.40.0
- **AI/LLM:** Ollama (local LLM)
- **Async:** AsyncIO for concurrent processing
- **Rate Limiting:** SlowAPI

### Frontend
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **Routing:** React Router
- **HTTP Client:** Fetch API

### Infrastructure
- **Process Management:** Multiprocessing (Windows isolation)
- **Task Scheduling:** AsyncIO (replaces `schedule` library)
- **Logging:** Python logging with custom colored formatter

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 13+
- Ollama (for AI form detection)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd GENIE-OPS-Prototype
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   pip install -r requirements.txt
   
   # Install Playwright browsers
   playwright install chromium
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   ```

4. **Database Setup:**
   ```bash
   # Create PostgreSQL database
   createdb genie_ops
   
   # Update DATABASE_URL in backend/.env or config.py
   # Default: postgresql://postgres:postgres@localhost:5432/genie_ops
   ```

5. **Ollama Setup:**
   ```bash
   # Install Ollama from https://ollama.ai
   # Pull the model
   ollama pull llama3.2:3b
   ```

6. **Environment Variables:**
   ```bash
   # Backend .env (optional, uses config.py defaults)
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/genie_ops
   OLLAMA_BASE_URL=http://localhost:11434
   LLM_MODEL=llama3.2:3b
   
   # Frontend .env
   VITE_API_BASE_URL=http://localhost:8000
   ```

### Running the Application

1. **Start PostgreSQL:**
   ```bash
   # Ensure PostgreSQL is running
   ```

2. **Start Ollama:**
   ```bash
   ollama serve
   ```

3. **Start Backend:**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

4. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

5. **Access the Application:**
   - Frontend: http://localhost:5173
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

---

## 🔄 How It Works

### Submission Workflow

1. **User Creates SaaS Product**
   - User enters SaaS details (name, URL, description, category, email, logo)
   - System stores in database

2. **User Adds Directories**
   - User adds directory URLs where they want to submit
   - System stores directory information

3. **User Starts Submission Job**
   - User selects SaaS product and directories
   - System creates submission records (status: "pending")
   - Workflow manager picks up pending submissions

4. **Workflow Manager Processes Submission**
   - Checks submission status (skips if already submitted)
   - Creates workflow instance
   - Assigns browser worker (session-based)

5. **Form Detection & Analysis (Brain)**
   - Browser navigates to directory URL
   - System extracts form HTML
   - AI analyzes form structure (or uses DOM fallback)
   - Returns field mappings and selectors

6. **Form Filling (Hands)**
   - System maps SaaS data to form fields
   - Fills text inputs, selects, textareas
   - Uploads logo file (if applicable)
   - Verifies values are set correctly

7. **Form Submission**
   - System finds and clicks submit button
   - Waits for confirmation/redirect
   - Detects success/error messages
   - Takes screenshot for debugging

8. **Status Update**
   - System updates submission status:
     - **Success:** "submitted" → "approved" (when confirmed)
     - **Error:** "failed" (with error message)
     - **Retry:** Resets to "pending" and increments retry count

9. **Dashboard Updates**
   - Frontend polls for updates (5s when active, 30s when idle)
   - Displays real-time progress and status
   - Shows statistics and success rates

### Status Flow

```
pending → processing → submitted → approved
                ↓
             failed → (retry) → pending
```

---

## 📚 API Documentation

Full API documentation is available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Documentation:** See [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)

### Key Endpoints

- `POST /api/jobs/start-submission` - Start submission job
- `GET /api/submissions` - List submissions
- `GET /api/submissions/stats/summary` - Get statistics
- `POST /api/submissions/{id}/retry` - Retry failed submission
- `GET /api/jobs/workflow/status` - Get workflow status

### Rate Limits

- **Default:** 100 requests/minute
- **Authentication:** 10 requests/minute
- **Submissions:** 30 requests/minute
- **Jobs:** 20 requests/minute
- **Statistics:** 60 requests/minute

---

## ⚙️ Configuration

Configuration is managed in `backend/app/core/config.py`:

```python
# Database
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/genie_ops"

# AI/LLM
OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "llama3.2:3b"

# Automation
PLAYWRIGHT_HEADLESS = True
BROWSER_WORKER_POOL_SIZE = 1
BROWSER_WORKER_TIMEOUT = 60

# Workflow
WORKFLOW_MAX_CONCURRENT = 1
WORKFLOW_PROCESSING_INTERVAL = 30
WORKFLOW_MAX_RETRIES = 3
```

See [docs/QUICK_START.md](docs/QUICK_START.md) for detailed configuration options.

---

## 📁 Project Structure

```
GENIE-OPS-Prototype/
├── backend/
│   ├── app/
│   │   ├── ai/                 # AI Form Reader (Brain)
│   │   │   └── form_reader.py
│   │   ├── api/                # FastAPI routes
│   │   │   ├── auth.py
│   │   │   ├── saas.py
│   │   │   ├── directories.py
│   │   │   ├── submissions.py
│   │   │   └── jobs.py
│   │   ├── automation/         # Browser Automation (Hands)
│   │   │   ├── browser.py
│   │   │   ├── browser_worker.py
│   │   │   └── browser_pool.py
│   │   ├── workflow/           # Workflow Manager (Control Center)
│   │   │   ├── manager.py
│   │   │   └── submitter.py
│   │   ├── db/                 # Database models and CRUD
│   │   │   ├── models.py
│   │   │   ├── crud.py
│   │   │   └── session.py
│   │   ├── core/               # Core configuration
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── utils/              # Utilities
│   │   │   ├── logger.py
│   │   │   └── rate_limit.py
│   │   └── main.py            # FastAPI app entry point
│   ├── test/                   # Test files
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/              # React pages
│   │   │   ├── Dashboard.tsx
│   │   │   ├── SaaSForm.tsx
│   │   │   └── Submissions.tsx
│   │   ├── api/                # API client
│   │   └── components/         # React components
│   └── package.json
├── docs/                       # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── QUICK_START.md
│   └── STATUS_REPORT.md
└── README.md
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest test/
```

### End-to-End Test

```bash
cd backend/test
python test_submission.py
```

See [backend/test/README_TESTING.md](backend/test/README_TESTING.md) for more details.

---

## 🚢 Deployment

### Production Considerations

1. **Database:** Use managed PostgreSQL (AWS RDS, Azure, etc.)
2. **Environment Variables:** Set all sensitive values in environment
3. **Rate Limiting:** Consider Redis for distributed rate limiting
4. **Monitoring:** Add logging and monitoring (Sentry, DataDog, etc.)
5. **Security:** Enable authentication and HTTPS
6. **Scaling:** Use process managers (PM2, Supervisor) or container orchestration

### Docker (Future)

```bash
# Build and run with docker-compose
docker-compose up -d
```

---

## 🤝 Contributing

This is a prototype project. For production use:

1. Add comprehensive error handling
2. Implement full authentication
3. Add unit and integration tests
4. Set up CI/CD pipeline
5. Add monitoring and alerting
6. Document deployment procedures

---

## 📝 License

This project is part of a coding assessment. See the original requirements in [docs/context.txt](docs/context.txt).

---

## 🙏 Acknowledgments

- **FastAPI** for the excellent async framework
- **Playwright** for robust browser automation
- **Ollama** for local LLM capabilities
- **React** and **Tailwind CSS** for the modern UI

---

## 📞 Support

For questions or issues:
- Check [docs/QUICK_START.md](docs/QUICK_START.md) for setup help
- Review [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) for API details
- See [docs/STATUS_REPORT.md](docs/STATUS_REPORT.md) for project status

---

**Please hire me**
