# Post API - FastAPI Backend

Backend API for posting system with JWT authentication and MinIO image storage.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose)
- **Object Storage**: MinIO

## Quick Start

### 1. Prerequisites

- Python 3.10+
- PostgreSQL
- MinIO

### 2. Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env
# Edit .env with your configuration
```

### 3. Configure Environment

Edit `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
SECRET_KEY=your-secret-key-here
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### 4. Run Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### 5. Start Server

```bash
uvicorn app.main:app --reload
```

API will be available at: `http://localhost:8000`

Swagger UI: `http://localhost:8000/docs`

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login (returns tokens) |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Get current user |

### Posts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/posts` | List all posts |
| GET | `/posts/{id}` | Get single post |
| POST | `/posts` | Create post (auth required) |
| PUT | `/posts/{id}` | Update post (owner only) |
| DELETE | `/posts/{id}` | Delete post (owner only) |
| GET | `/posts/user/me` | Get my posts (auth required) |

## Project Structure

```
app/
├── main.py           # FastAPI entry point
├── config.py         # Environment configuration
├── database.py       # Database connection
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── api/              # API routes
│   ├── deps.py       # Dependencies
│   └── routes/       # Route handlers
├── services/         # Business logic
└── utils/            # Utility functions
```

## License

MIT
