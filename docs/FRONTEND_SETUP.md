# Frontend Setup Guide

## Installation

1. **Install React Router** (if not already installed):
   ```bash
   cd frontend
   npm install react-router-dom --legacy-peer-deps
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```

## Features

### Pages

1. **Dashboard** (`/`)
   - Overview statistics
   - Workflow manager status
   - Real-time updates every 30 seconds

2. **SaaS Products** (`/saas`)
   - List all SaaS products
   - Create new products
   - Edit existing products
   - Start submission jobs
   - Delete products

3. **Submissions** (`/submissions`)
   - View all submissions
   - Filter by SaaS or status
   - Retry failed submissions
   - Process pending submissions
   - Real-time updates every 10 seconds

### Theme

The frontend uses a Cursor-inspired dark theme with:
- Dark background (`#0d1117`)
- Surface cards (`#161b22`)
- Accent blue (`#58a6ff`)
- Modern typography (Inter font)
- Smooth transitions and hover effects

### API Integration

All API calls are configured to use:
- Base URL: `http://localhost:8000` (configurable via `VITE_API_BASE_URL`)
- Automatic error handling
- JSON request/response format

## Configuration

Create a `.env` file in the `frontend/` directory:
```env
VITE_API_BASE_URL=http://localhost:8000
```

## Development

The frontend is built with:
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router** - Navigation

## Notes

- The frontend requires the backend API to be running
- Authentication is currently bypassed (for development)
- All API endpoints expect JSON responses
