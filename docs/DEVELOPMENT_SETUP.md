# Development Setup Guide

## Prerequisites

Ensure you have the following installed:

- **Node.js**: Version 18.0.0 or higher
  ```bash
  node --version  # Should be 18.0.0+
  ```

- **Python**: Version 3.11 or higher
  ```bash
  python --version  # Should be 3.11+
  ```

- **PostgreSQL**: Version 14 or higher
  ```bash
  psql --version  # Should be 14+
  ```

- **Git**: For version control
  ```bash
  git --version
  ```

## Environment Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd fantasy-football-assistant
```

### 2. Backend Setup

#### Create Python Virtual Environment
```bash
cd backend
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

#### Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Environment Variables
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/fantasy_football_db

# ESPN Configuration  
ESPN_LEAGUE_ID=your_league_id_here
ESPN_S2=your_espn_s2_cookie_here
ESPN_SWID=your_espn_swid_cookie_here
ESPN_SEASON_YEAR=2024

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Development
DEBUG=true
RELOAD=true
```

### 3. Database Setup

#### Create Database
```bash
# Connect to PostgreSQL as superuser
psql postgres

# Create database and user
CREATE DATABASE fantasy_football_db;
CREATE USER fantasy_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE fantasy_football_db TO fantasy_user;
\q
```

#### Run Database Migrations
```bash
# From backend/ directory with activated virtual environment
alembic upgrade head
```

#### Verify Database Connection
```bash
# Test database connection
python -c "
from app.db.database import get_database_url
print('Database URL configured successfully')
print(get_database_url())
"
```

### 4. Frontend Setup

#### Install Node Dependencies
```bash
cd ../frontend
npm install
```

#### Environment Configuration
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```bash
VITE_API_URL=http://localhost:8000/api
VITE_ESPN_LEAGUE_ID=your_league_id
```

#### Verify Frontend Setup
```bash
npm run type-check
npm run lint
```

## Development Workflow

### Starting Development Servers

#### Backend (Terminal 1)
```bash
cd backend
source venv/bin/activate  # Activate virtual environment
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access points:
- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

#### Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

Access: http://localhost:3000

### Development Commands

#### Backend Commands
```bash
# Run tests
pytest

# Format code
black .
isort .

# Lint code
flake8

# Type checking
mypy .

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head

# Run development server
uvicorn app.main:app --reload
```

#### Frontend Commands
```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix

# Testing
npm run test
npm run test:watch
```

## Database Schema

### Core Tables

#### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### leagues
```sql
CREATE TABLE leagues (
    id SERIAL PRIMARY KEY,
    espn_league_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    season_year INTEGER NOT NULL,
    size INTEGER NOT NULL,
    espn_s2 TEXT,
    espn_swid TEXT,
    owner_user_id INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### teams
```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    espn_team_id INTEGER NOT NULL,
    league_id INTEGER REFERENCES leagues(id),
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    nickname VARCHAR(255),
    abbreviation VARCHAR(10),
    owner_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(league_id, espn_team_id)
);
```

#### players
```sql
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    espn_player_id INTEGER UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    position_id INTEGER NOT NULL,
    pro_team_id INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Running Migrations

```bash
# Generate new migration after model changes
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback last migration  
alembic downgrade -1

# View migration history
alembic history --verbose
```

## Code Quality and Standards

### Python (Backend)
- **Formatting**: Black with line length 88
- **Import sorting**: isort compatible with Black
- **Linting**: flake8 with extensions
- **Type checking**: mypy with strict mode
- **Testing**: pytest with async support

### TypeScript/React (Frontend)
- **Formatting**: Prettier with 2-space indents
- **Linting**: ESLint with React and TypeScript rules
- **Type checking**: TypeScript strict mode
- **Testing**: Vitest for unit tests, Playwright for E2E

### Git Workflow
- **Branches**: Use feature branches for development
- **Commits**: Conventional commit messages
- **Pre-commit**: Hooks for formatting and linting

## ESPN Cookie Setup

### Finding Your ESPN Cookies

1. **Login to ESPN Fantasy Football**
   - Navigate to https://fantasy.espn.com
   - Log in with your ESPN account
   - Go to your league's main page

2. **Open Browser Developer Tools**
   - Chrome/Edge: Press F12 or Ctrl+Shift+I
   - Firefox: Press F12 or Ctrl+Shift+I
   - Safari: Enable Developer menu, then press Cmd+Opt+I

3. **Navigate to Cookies**
   - Chrome: Application tab → Storage → Cookies → https://fantasy.espn.com
   - Firefox: Storage tab → Cookies → https://fantasy.espn.com
   - Safari: Storage tab → Cookies → https://fantasy.espn.com

4. **Copy Cookie Values**
   - Find `espn_s2`: Copy the entire value (usually starts with "AEB")
   - Find `SWID`: Copy the value including curly braces `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`

### Testing ESPN Integration

```bash
# From backend/ directory with activated virtual environment
python -c "
import asyncio
from app.services.espn_service import ESPNService

async def test_connection():
    service = ESPNService()
    try:
        league_data = await service.get_league_info()
        print('ESPN connection successful!')
        print(f'League: {league_data.name}')
        print(f'Teams: {len(league_data.teams)}')
    except Exception as e:
        print(f'ESPN connection failed: {e}')

asyncio.run(test_connection())
"
```

## Troubleshooting

### Common Issues

#### Backend Won't Start
- **Virtual environment not activated**: Run `source venv/bin/activate`
- **Missing dependencies**: Run `pip install -r requirements.txt`
- **Database connection error**: Check PostgreSQL is running and credentials are correct
- **Port already in use**: Kill process on port 8000 or use different port

#### Frontend Won't Start  
- **Node modules missing**: Run `npm install`
- **Node version too old**: Upgrade to Node 18+
- **Port conflict**: Stop other services on port 3000

#### ESPN API Issues
- **401 Unauthorized**: Check your ESPN cookies are valid and current
- **403 Forbidden**: Verify you have access to the league
- **League not found**: Confirm league ID is correct
- **Cookies expired**: Re-obtain cookies from browser

#### Database Issues
- **Connection refused**: Ensure PostgreSQL is running
- **Database doesn't exist**: Create database with `createdb fantasy_football_db`
- **Migration errors**: Reset database and re-run migrations

### Getting Help

1. **Check logs**: Both frontend and backend provide detailed error logs
2. **API documentation**: Visit http://localhost:8000/docs for interactive API testing
3. **Database inspection**: Use psql or pgAdmin to inspect database state
4. **Network debugging**: Use browser dev tools to inspect API calls

### Development Tips

- **API Testing**: Use the FastAPI docs interface at `/docs` for testing endpoints
- **Database Inspection**: Use `psql fantasy_football_db` to inspect data
- **Hot Reload**: Both servers support hot reload for rapid development
- **Debugging**: Use debugger breakpoints in VS Code for both Python and TypeScript
- **Environment Isolation**: Always use virtual environment for Python dependencies