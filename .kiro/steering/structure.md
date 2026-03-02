# Project Structure

## Directory Organization

```
src/
├── backend/           # Backend logic and data layer
│   ├── config/       # Database configuration and initialization
│   ├── entities/     # SQLAlchemy ORM models
│   ├── repositories/ # Data access layer (repository pattern)
│   ├── services/     # Business logic layer
│   └── seed/         # Database seeding scripts and data
├── frontend/         # GUI components
└── main.py          # Application entry point
```

## Architecture Pattern

The application follows a **layered architecture** with clear separation of concerns:

### Backend Layers

1. **Entities** (`backend/entities/`)
   - SQLAlchemy ORM models defining database schema
   - Models: `Participante`, `Questao`, `Resposta`, `Config`
   - Relationships defined using SQLAlchemy's `relationship()`

2. **Repositories** (`backend/repositories/`)
   - Data access layer implementing repository pattern
   - Each entity has a corresponding repository (e.g., `ParticipanteRepo`)
   - Handle all database queries using `DBConnectionHandler` context manager
   - Return dictionaries instead of ORM objects for decoupling

3. **Services** (`backend/services/`)
   - Business logic layer
   - Services: `PresenceService`, `QuestionService`, `RankingService`
   - Orchestrate repository calls and implement business rules
   - Handle Excel import/export operations

4. **Config** (`backend/config/`)
   - `base.py`: SQLAlchemy declarative base
   - `connection.py`: Database connection handler (context manager pattern)
   - `db_init.py`: Database initialization logic

### Frontend Layer

- **Frontend** (`frontend/`)
  - CustomTkinter-based GUI components
  - `app.py`: Main application window and layout
  - Component modules: `lista.py`, `gabarito.py`, `rank.py`, `configuracoes.py`
  - `theme.py`: Color scheme and styling constants

## Key Conventions

### Database Access Pattern

Always use the `DBConnectionHandler` context manager for database operations:

```python
with DBConnectionHandler() as db:
    result = db.session.query(Entity).filter(...).all()
```

### Repository Return Format

Repositories return lists of dictionaries, not ORM objects:

```python
return [{"id": p.id, "nome": p.nome} for p in participantes]
```

### Service Initialization

Services instantiate their own repository instances in `__init__`:

```python
def __init__(self):
    self.repo = ParticipanteRepo()
```

### Import Paths

Use absolute imports from `src/` root:
- Backend: `from backend.entities.participante import Participante`
- Frontend: `from frontend.lista import Lista`

## File Naming

- Python files: snake_case (e.g., `presence_service.py`)
- Classes: PascalCase (e.g., `PresenceService`)
- Database file: `database.db` in `src/backend/`
