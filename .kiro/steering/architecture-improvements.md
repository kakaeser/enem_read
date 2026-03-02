# Architecture Improvements for FastAPI + Flutter Migration

## Current Architecture Analysis

### Strengths
- Clean layered architecture (Entities → Repositories → Services)
- Repository pattern already implemented
- Services return dictionaries (good for JSON serialization)
- SQLAlchemy ORM (compatible with FastAPI)
- Clear separation between backend and frontend

### Critical Issues for Web Migration

1. **Tight Coupling**: Services instantiate repositories directly in `__init__`
2. **No DTOs/Schemas**: Dictionary returns lack type safety and validation
3. **No API Layer**: Business logic mixed with data transformation
4. **Session Management**: Context manager pattern won't work with async FastAPI
5. **No Authentication/Authorization**: Required for web APIs
6. **File Operations**: Excel import/export in services (should be in API layer)
7. **No Error Handling**: Missing standardized error responses
8. **No Pagination**: Will cause performance issues with large datasets

## Recommended Refactoring Strategy

### Phase 1: Decouple Dependencies (Do This First)

#### 1.1 Implement Dependency Injection

**Current Problem:**
```python
class PresenceService:
    def __init__(self):
        self.repo = ParticipanteRepo()  # Hard-coded dependency
```

**Solution:**
```python
class PresenceService:
    def __init__(self, repo: ParticipanteRepo):
        self.repo = repo  # Injected dependency
```

**Benefits:**
- Easy to swap implementations (e.g., mock repos for testing)
- FastAPI's dependency injection will work seamlessly
- Testable without database

#### 1.2 Create Abstract Repository Interfaces

```python
# backend/repositories/interfaces/participante_interface.py
from abc import ABC, abstractmethod
from typing import List, Optional

class IParticipanteRepo(ABC):
    @abstractmethod
    def listar_ordem_alfabetica(self) -> List[dict]:
        pass
    
    @abstractmethod
    def marcar_presenca(self, user_id: int, mark: int) -> bool:
        pass
```

**Benefits:**
- Services depend on interfaces, not concrete implementations
- Can create different implementations (SQL, NoSQL, in-memory)
- Follows SOLID principles

### Phase 2: Add DTOs/Schemas (Pydantic)

#### 2.1 Create Pydantic Models

```python
# backend/schemas/participante.py
from pydantic import BaseModel, Field
from typing import Optional

class ParticipanteBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)

class ParticipanteCreate(ParticipanteBase):
    pass

class ParticipanteUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    presente: Optional[bool] = None

class ParticipanteResponse(ParticipanteBase):
    id: int
    presente: bool
    
    class Config:
        from_attributes = True  # For SQLAlchemy compatibility
```

**Benefits:**
- Type safety and validation
- Auto-generated API documentation
- Clear contracts between layers
- Easy serialization/deserialization

#### 2.2 Update Services to Use Schemas

```python
from backend.schemas.participante import ParticipanteResponse

class PresenceService:
    def listar_nomes(self) -> List[ParticipanteResponse]:
        data = self.repo.listar_ordem_alfabetica()
        return [ParticipanteResponse(**p) for p in data]
```

### Phase 3: Async Database Support

#### 3.1 Migrate to Async SQLAlchemy

**Current (Sync):**
```python
with DBConnectionHandler() as db:
    result = db.session.query(Participante).all()
```

**Future (Async for FastAPI):**
```python
async with AsyncDBConnectionHandler() as db:
    result = await db.session.execute(
        select(Participante)
    )
    return result.scalars().all()
```

**Implementation:**
```python
# backend/config/async_connection.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

class AsyncDBConnectionHandler:
    _engine = None
    
    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            cls._engine = create_async_engine(
                "sqlite+aiosqlite:///database.db",
                echo=False
            )
        return cls._engine
    
    @classmethod
    async def get_session(cls) -> AsyncSession:
        async_session = async_sessionmaker(
            cls.get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
        async with async_session() as session:
            yield session
```

**Benefits:**
- Non-blocking I/O for better performance
- Required for FastAPI async endpoints
- Handles concurrent requests efficiently

### Phase 4: Add API Layer (Controllers)

#### 4.1 Create Controller/Router Structure

```python
# backend/api/v1/endpoints/participantes.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend.schemas.participante import ParticipanteResponse, ParticipanteCreate
from backend.services.presence_service import PresenceService
from backend.api.dependencies import get_presence_service

router = APIRouter(prefix="/participantes", tags=["participantes"])

@router.get("/", response_model=List[ParticipanteResponse])
async def listar_participantes(
    service: PresenceService = Depends(get_presence_service)
):
    """Lista todos os participantes em ordem alfabética"""
    return service.listar_nomes()

@router.post("/{participante_id}/presenca", response_model=dict)
async def marcar_presenca(
    participante_id: int,
    presente: bool,
    service: PresenceService = Depends(get_presence_service)
):
    """Marca ou desmarca presença de um participante"""
    success = service.marcar_presenca(participante_id, int(presente))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participante não encontrado"
        )
    return {"success": True}
```

#### 4.2 Dependency Injection Setup

```python
# backend/api/dependencies.py
from fastapi import Depends
from backend.repositories.participante_repo import ParticipanteRepo
from backend.services.presence_service import PresenceService

def get_participante_repo() -> ParticipanteRepo:
    return ParticipanteRepo()

def get_presence_service(
    repo: ParticipanteRepo = Depends(get_participante_repo)
) -> PresenceService:
    return PresenceService(repo)
```

### Phase 5: Error Handling & Validation

#### 5.1 Custom Exception Classes

```python
# backend/core/exceptions.py
class AppException(Exception):
    """Base exception for application errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)

class ValidationException(AppException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=422)
```

#### 5.2 Global Exception Handler

```python
# backend/api/middleware/error_handler.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from backend.core.exceptions import AppException

async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "status_code": exc.status_code
        }
    )
```

### Phase 6: Add Pagination & Filtering

#### 6.1 Pagination Schema

```python
# backend/schemas/pagination.py
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

#### 6.2 Repository with Pagination

```python
def listar_ordem_alfabetica(
    self, 
    offset: int = 0, 
    limit: int = 20
) -> tuple[List[dict], int]:
    with DBConnectionHandler() as db:
        query = db.session.query(Participante).order_by(Participante.nome)
        
        total = query.count()
        participantes = query.offset(offset).limit(limit).all()
        
        return (
            [{"id": p.id, "nome": p.nome, "presente": p.presente} 
             for p in participantes],
            total
        )
```

### Phase 7: Authentication & Authorization

#### 7.1 Add User Model

```python
# backend/entities/user.py
from sqlalchemy import Column, Integer, String, Boolean
from backend.config.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
```

#### 7.2 JWT Authentication

```python
# backend/core/security.py
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "your-secret-key"  # Use environment variable
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### Phase 8: File Upload Handling

#### 8.1 Move Excel Import to API Layer

```python
# backend/api/v1/endpoints/import_export.py
from fastapi import APIRouter, UploadFile, File, Depends
import pandas as pd
from io import BytesIO

router = APIRouter(prefix="/import", tags=["import"])

@router.post("/participantes")
async def importar_participantes(
    file: UploadFile = File(...),
    service: PresenceService = Depends(get_presence_service)
):
    """Importa lista de participantes de arquivo Excel"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Arquivo deve ser Excel (.xlsx ou .xls)")
    
    contents = await file.read()
    df = pd.read_excel(BytesIO(contents))
    
    if "Nome" not in df.columns:
        raise HTTPException(400, "Arquivo deve conter coluna 'Nome'")
    
    nomes = [nome.strip() for nome in df["Nome"].dropna() if nome.strip()]
    service.importar_lista(nomes)
    
    return {"message": f"{len(nomes)} participantes importados"}
```

## Proposed New Structure

```
src/
├── backend/
│   ├── api/                    # NEW: API layer
│   │   ├── v1/
│   │   │   ├── endpoints/      # Route handlers
│   │   │   │   ├── participantes.py
│   │   │   │   ├── questoes.py
│   │   │   │   ├── ranking.py
│   │   │   │   └── auth.py
│   │   │   └── router.py       # Aggregate routers
│   │   ├── dependencies.py     # Dependency injection
│   │   └── middleware/         # Error handlers, CORS, etc.
│   ├── core/                   # NEW: Core utilities
│   │   ├── config.py           # Settings (use pydantic-settings)
│   │   ├── security.py         # Auth utilities
│   │   └── exceptions.py       # Custom exceptions
│   ├── schemas/                # NEW: Pydantic models
│   │   ├── participante.py
│   │   ├── questao.py
│   │   ├── resposta.py
│   │   └── pagination.py
│   ├── entities/               # SQLAlchemy models (unchanged)
│   ├── repositories/
│   │   ├── interfaces/         # NEW: Abstract interfaces
│   │   └── implementations/    # Concrete implementations
│   ├── services/               # Business logic (refactored)
│   └── config/                 # DB config (add async support)
├── frontend/                   # Keep for now, replace with Flutter later
└── main.py                     # FastAPI app entry point
```

## Migration Checklist

### Immediate Actions (Can Do Now)
- [ ] Add Pydantic schemas for all entities
- [ ] Implement dependency injection in services
- [ ] Create repository interfaces
- [ ] Add proper error handling and custom exceptions
- [ ] Implement pagination in repositories
- [ ] Add input validation using Pydantic
- [ ] Create unit tests for services (now possible with DI)

### Pre-FastAPI Migration
- [ ] Migrate to async SQLAlchemy
- [ ] Create API layer structure
- [ ] Implement JWT authentication
- [ ] Add CORS middleware configuration
- [ ] Move file operations to API layer
- [ ] Create API documentation structure

### During FastAPI Migration
- [ ] Create FastAPI app instance
- [ ] Register all routers
- [ ] Add middleware (CORS, error handling, logging)
- [ ] Implement rate limiting
- [ ] Add health check endpoints
- [ ] Configure environment-based settings

### Post-Migration (Flutter Integration)
- [ ] Design RESTful API contracts
- [ ] Implement WebSocket for real-time updates (optional)
- [ ] Add API versioning strategy
- [ ] Create comprehensive API documentation
- [ ] Implement caching strategy (Redis)
- [ ] Add monitoring and logging (Sentry, ELK)

## Key Principles for Refactoring

1. **Dependency Inversion**: Depend on abstractions, not concretions
2. **Single Responsibility**: Each class/function does one thing
3. **Open/Closed**: Open for extension, closed for modification
4. **Type Safety**: Use Pydantic for all data transfer
5. **Async First**: Prepare for async operations
6. **Testability**: Design for easy unit testing
7. **API-First**: Think in terms of HTTP endpoints

## Database Migration Considerations

### Current: SQLite
- Good for desktop app
- File-based, no server needed
- Limited concurrency

### Future: PostgreSQL (Recommended for Web)
- Better concurrency support
- ACID compliance
- JSON field support
- Full-text search
- Better for production web apps

**Migration Path:**
1. Keep SQLite for development
2. Use PostgreSQL for production
3. SQLAlchemy makes this transparent (just change connection string)

## Testing Strategy

```python
# tests/services/test_presence_service.py
import pytest
from unittest.mock import Mock
from backend.services.presence_service import PresenceService

def test_listar_nomes():
    # Mock repository
    mock_repo = Mock()
    mock_repo.listar_ordem_alfabetica.return_value = [
        {"id": 1, "nome": "Alice", "presente": True}
    ]
    
    # Inject mock
    service = PresenceService(repo=mock_repo)
    
    # Test
    result = service.listar_nomes()
    assert len(result) == 1
    assert result[0]["nome"] == "Alice"
```

## Performance Considerations

1. **Connection Pooling**: Configure SQLAlchemy pool size
2. **Query Optimization**: Use eager loading for relationships
3. **Caching**: Add Redis for frequently accessed data
4. **Indexing**: Add database indexes on foreign keys and search fields
5. **Batch Operations**: Use bulk inserts/updates where possible

## Security Checklist

- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (SQLAlchemy handles this)
- [ ] XSS prevention (sanitize outputs)
- [ ] CSRF protection (for web forms)
- [ ] Rate limiting per IP/user
- [ ] Secure password hashing (bcrypt)
- [ ] JWT token expiration
- [ ] HTTPS only in production
- [ ] Environment variables for secrets
- [ ] CORS configuration (whitelist origins)
