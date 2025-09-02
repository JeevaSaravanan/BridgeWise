# BridgeWise Backend API

This FastAPI backend provides portfolio management functionality with PostgreSQL database integration.

## Features

- Portfolio item CRUD operations
- GitHub repository analysis
- Portfolio statistics and search
- Data import/export functionality
- CORS support for frontend integration

## Prerequisites

- Python 3.8+
- PostgreSQL database
- Environment variables configured in `.env`

## Setup

1. Install dependencies:
   ```bash
   cd github-analyzer-api
   pip install -r requirements.txt
   ```

2. Ensure PostgreSQL is running and database is set up:
   ```bash
   # Run from project root
   ./setup-postgres.sh
   ```

3. Start the API server:
   ```bash
   ./start.sh
   ```

The API will be available at:
- Main API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Endpoints

### Portfolio Management
- `GET /api/portfolio` - Get all portfolio items
- `POST /api/portfolio` - Create new portfolio item
- `PUT /api/portfolio/{id}` - Update portfolio item
- `DELETE /api/portfolio/{id}` - Delete portfolio item
- `GET /api/portfolio/stats` - Get portfolio statistics
- `GET /api/portfolio/search?q={query}` - Search portfolio items
- `POST /api/portfolio/import` - Import portfolio data
- `POST /api/portfolio/seed` - Seed sample data

### GitHub Analysis
- `POST /analyze` - Analyze GitHub repository

## Database Schema

The API uses the existing PostgreSQL schema with the `portfolio_items` table:

```sql
CREATE TABLE portfolio_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    url TEXT,
    summary TEXT NOT NULL,
    skills JSONB,
    thumbnail VARCHAR(10) DEFAULT '📄',
    analysis_result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Environment Variables

Required environment variables (configured in `.env`):

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bridgewise_db
DB_USER=bridgewise_user
DB_PASSWORD=your_secure_password
```

## Development

To run in development mode with auto-reload:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
