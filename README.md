# Fantasy Football Assistant

A comprehensive web application that connects to ESPN Fantasy Football leagues to provide intelligent trade suggestions, waiver wire recommendations, and real-time alerts to optimize your fantasy football experience.

## Features

- **ESPN League Integration**: Seamlessly connect to your ESPN Fantasy Football leagues
- **Trade Analyzer**: Get intelligent trade suggestions based on player valuations and team needs
- **Waiver Wire Assistant**: Receive recommendations for pickup targets and drop candidates
- **Real-time Alerts**: Get notified about injuries, breakout performances, and opportunities
- **Team Optimization**: Lineup suggestions and roster management tools
- **Mobile-Responsive UI**: Access your tools on any device

## Tech Stack

**Frontend**
- React 18 with TypeScript
- Vite for fast development and building
- Tailwind CSS for styling
- React Router for navigation
- Recharts for data visualization
- Headless UI for accessible components

**Backend**
- FastAPI with async/await support
- SQLAlchemy 2.0 with async PostgreSQL
- Pydantic for data validation
- JWT authentication
- Alembic for database migrations

**Database**
- PostgreSQL with asyncpg driver
- Connection pooling for optimal performance

## Installation

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL 14+

### Quick Start

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd fantasy-football-assistant
   ```

2. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Database setup**
   ```bash
   # Create PostgreSQL database
   createdb fantasy_football_db
   
   # Run migrations
   alembic upgrade head
   ```

4. **Environment configuration**
   ```bash
   # Copy and configure environment files
   cp .env.example .env
   # Edit .env with your ESPN credentials and database settings
   ```

5. **Frontend setup**
   ```bash
   cd ../frontend
   npm install
   ```

6. **Start development servers**
   ```bash
   # Terminal 1: Backend (from backend/)
   uvicorn app.main:app --reload
   
   # Terminal 2: Frontend (from frontend/)
   npm run dev
   ```

7. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## ESPN Integration Setup

To connect to your ESPN league, you'll need:

1. **League ID**: Found in your ESPN league URL
2. **ESPN Cookies**: Required for private leagues
   - `espn_s2`: Authentication cookie
   - `SWID`: Session identifier

See [ESPN_API_INTEGRATION.md](docs/ESPN_API_INTEGRATION.md) for detailed setup instructions.

## Development

- **Frontend**: Hot reload enabled with Vite
- **Backend**: Auto-reload enabled with uvicorn
- **Database**: Migrations managed with Alembic
- **Type Safety**: Full TypeScript on frontend, Pydantic validation on backend

## Project Structure

```
fantasy-football-assistant/
├── frontend/           # React frontend application
├── backend/            # FastAPI backend application  
├── shared/             # Shared types and utilities
├── docs/               # Project documentation
├── scripts/            # Build and deployment scripts
└── docker/             # Docker configuration files
```

## Contributing

1. Follow the development setup in [DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md)
2. Use conventional commits for clear git history
3. Ensure all tests pass before submitting PRs
4. Maintain type safety and add proper validation

## License

MIT License - see LICENSE file for details