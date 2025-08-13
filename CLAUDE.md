# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a full-stack lottery analysis application with AI/ML capabilities for predicting lottery numbers and analyzing patterns.

### Backend Structure
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with SQLAlchemy ORM 
- **AI/ML**: Random Forest and LSTM models using scikit-learn and PyTorch
- **Architecture**: Modular API with separate routers for different functionalities
- **Key Components**:
  - `backend/app/core/ai_model.py` - ML model management and training
  - `backend/app/core/data_manager.py` - Data fetching and database operations
  - `backend/app/core/lottery_context.py` - Context switching between lottery types
  - `backend/app/api/` - REST API endpoints organized by functionality
  - `backend/app/models/` - Pydantic schemas and data models

### Frontend Structure
- **Framework**: React 18 with TypeScript
- **UI**: Material-UI (MUI) + Tailwind CSS
- **State Management**: Zustand + React Query for server state
- **Routing**: React Router v6
- **Key Features**:
  - Authentication with JWT
  - Real-time lottery analysis and predictions
  - Interactive charts using Recharts
  - Responsive design with mobile support

### Data Architecture
- Multiple lottery types supported (4x20, 5x36plus)
- Context-based switching between lottery configurations
- Automated data scraping from lottery sources
- ML model training with caching and optimization

## Development Commands

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (FastAPI with uvicorn)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

# Run with Docker Compose (full stack)
docker-compose up
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev
# or
npm start

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint

# Testing
npm test
```

### Database Operations
- Database initialization is handled automatically on application startup
- SQLite databases are stored in `data/` directory
- Each lottery type has its own database file

## Key Development Patterns

### Lottery Context System
The application uses a context system to handle multiple lottery types:
```python
from backend.app.core.lottery_context import LotteryContext

with LotteryContext('4x20'):
    # All operations will use 4x20 lottery configuration
    data = data_manager.fetch_draws_from_db()
```

### ML Model Management
- Models are trained automatically on startup if sufficient data exists
- RF (Random Forest) models are preferred for reliability
- LSTM models provide additional prediction capabilities
- Model caching is implemented for performance

### API Structure
- All lottery-specific endpoints use path parameter: `/api/v1/{lottery_type}/endpoint`
- Authentication endpoints are separate: `/api/v1/auth/`
- Subscription management: `/api/v1/subscriptions/`

### Frontend State Management
- Zustand for client state (auth, UI preferences)
- React Query for server state with automatic caching
- Form handling with React Hook Form + Yup validation

## Production Deployment

The application is configured for Docker deployment with:
- 4 API replicas with load balancing
- PostgreSQL with data persistence
- Redis for caching
- RabbitMQ for background tasks
- Nginx reverse proxy

## Environment Configuration

### Backend Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `RABBITMQ_URL` - RabbitMQ connection string

### Frontend Environment Variables
- `REACT_APP_API_URL` - Backend API base URL (defaults to development server)