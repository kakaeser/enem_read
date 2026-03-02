# Refactoring Roadmap: Desktop to Web Migration

## Overview

This document provides a step-by-step execution plan for refactoring the current desktop application to be web-ready for FastAPI + Flutter migration. The approach is incremental and non-breaking, allowing the desktop app to continue functioning while preparing for web deployment.

## Strategy: Parallel Architecture

Instead of breaking the existing app, we'll build the new architecture alongside it:

1. Create new modules (schemas, interfaces, core) without touching existing code
2. Gradually refactor services to use dependency injection
3. Keep both old and new code paths working
4. Once API layer is ready, deprecate desktop frontend

## Phase 1: Foundation (Week 1-2)

### Goal: Add type safety and prepare for dependency injection

#### Step 1.1: Install Additional Dependencies

```bash
pip install pydantic pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart aiosqlite
```

Update `requirements.txt`:
```
# Add these lines
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
aiosqlite==0.19.0
```

#### Step 1.2: Create Pydantic Schemas

Create `src/backend/schemas/` directory with these files:

**participante.py**
```python
from pydantic import BaseModel, Field
from typing import Optional

class ParticipanteBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255, description="Nome do participante")

class ParticipanteCreate(ParticipanteBase):
    """Schema para criação de participante"""
    pass

class ParticipanteUpdate(BaseModel):
    """Schema para atualização de participante"""
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    presente: Optional[bool] = None

class ParticipanteResponse(ParticipanteBase):
    """Schema para resposta de participante"""
    id: int
    presente: bool
    
    class Config:
        from_attributes = True
```

**questao.py**
```python
from pydantic import BaseModel, Field

class QuestaoBase(BaseModel):
    numero: int = Field(..., ge=1, description="Número da questão")
    peso: int = Field(1, ge=1, le=10, description="Peso da questão")

class QuestaoCreate(QuestaoBase):
    pass

class QuestaoResponse(QuestaoBase):
    id: int
    
    class Config:
        from_attributes = True
```

**resposta.py**
```python
from pydantic import BaseModel

class RespostaBase(BaseModel):
    user_id: int
    quest_id: int
    acertou: bool = False

class RespostaCreate(RespostaBase):
    pass

class RespostaResponse(RespostaBase):
    id: int
    
    class Config:
        from_attributes = True

class RespostaWithDetails(RespostaResponse):
    """Resposta com detalhes da questão"""
    numero_questao: int
    peso_questao: int
```

**ranking.py**
```python
from pydantic import BaseModel
from typing import Union

class RankingItem(BaseModel):
    nome: str
    nota: Union[float, str]  # Can be float or "-"
    
class RankingConfig(BaseModel):
    nota_max: float
    nota_simb: float
```

#### Step 1.3: Create Core Utilities

**src/backend/core/exceptions.py**
```python
class AppException(Exception):
    """Base exception for application errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundException(AppException):
    """Resource not found exception"""
    def __init__(self, resource: str, identifier: any):
        message = f"{resource} with id {identifier} not found"
        super().__init__(message, status_code=404)

class ValidationException(AppException):
    """Validation error exception"""
    def __init__(self, message: str):
        super().__init__(message, status_code=422)

class DuplicateException(AppException):
    """Duplicate resource exception"""
    def __init__(self, resource: str, field: str, value: any):
        message = f"{resource} with {field}='{value}' already exists"
        super().__init__(message, status_code=409)
```

**src/backend/core/config.py**
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./database.db"
    DATABASE_URL_ASYNC: str = "sqlite+aiosqlite:///./database.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    APP_NAME: str = "Enem da Read"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

Create `.env` file in project root:
```
SECRET_KEY=your-super-secret-key-here-change-in-production
DEBUG=True
```

## Phase 2: Repository Interfaces (Week 2-3)

### Goal: Decouple services from concrete implementations

#### Step 2.1: Create Repository Interfaces

**src/backend/repositories/interfaces/participante_interface.py**
```python
from abc import ABC, abstractmethod
from typing import List, Optional

class IParticipanteRepo(ABC):
    @abstractmethod
    def listar_ordem_alfabetica(self) -> List[dict]:
        """Lista participantes em ordem alfabética"""
        pass
    
    @abstractmethod
    def listar_presentes(self) -> List[dict]:
        """Lista apenas participantes presentes"""
        pass
    
    @abstractmethod
    def buscar_por_id(self, id: int) -> Optional[dict]:
        """Busca participante por ID"""
        pass
    
    @abstractmethod
    def buscar_por_nome(self, nome: str) -> Optional[dict]:
        """Busca participante por nome"""
        pass
    
    @abstractmethod
    def marcar_presenca(self, user_id: int, mark: int) -> bool:
        """Marca ou desmarca presença"""
        pass
    
    @abstractmethod
    def delete_participantes(self) -> bool:
        """Deleta todos os participantes"""
        pass
    
    @abstractmethod
    def criar_participantes(self, nomes: List[str]) -> None:
        """Cria múltiplos participantes"""
        pass
```

**src/backend/repositories/interfaces/questao_interface.py**
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from backend.entities.questao import Questao

class IQuestaoRepo(ABC):
    @abstractmethod
    def listar_ordem_numerica(self) -> List[dict]:
        pass
    
    @abstractmethod
    def buscar_por_numero(self, numero: int) -> Optional[dict]:
        pass
    
    @abstractmethod
    def add_questoes(self, questoes: List[Questao]) -> None:
        pass
    
    @abstractmethod
    def delete_questoes(self) -> bool:
        pass
```

**src/backend/repositories/interfaces/resposta_interface.py**
```python
from abc import ABC, abstractmethod
from typing import List, Optional

class IRespostaRepo(ABC):
    @abstractmethod
    def buscar_resposta(self, user_id: int, quest_id: int) -> Optional[dict]:
        pass
    
    @abstractmethod
    def buscar_respostas_participante(self, user_id: int) -> List[dict]:
        pass
    
    @abstractmethod
    def add_resposta(self, user_id: int, quest_id: int) -> None:
        pass
    
    @abstractmethod
    def mudar_acerto(self, user_id: int, quest_id: int, acertou: int) -> bool:
        pass
```

#### Step 2.2: Update Existing Repositories to Implement Interfaces

Modify `src/backend/repositories/participante_repo.py`:
```python
from backend.repositories.interfaces.participante_interface import IParticipanteRepo
from backend.entities.participante import Participante
from backend.config.connection import DBConnectionHandler
from typing import List, Optional

class ParticipanteRepo(IParticipanteRepo):
    # Keep all existing methods, just add interface inheritance
    # No other changes needed for now
    pass
```

Do the same for `questao_repo.py` and `resposta_repo.py`.

## Phase 3: Refactor Services with Dependency Injection (Week 3-4)

### Goal: Make services testable and flexible

#### Step 3.1: Refactor PresenceService

**Before:**
```python
class PresenceService:
    def __init__(self):
        self.repo = ParticipanteRepo()
```

**After:**
```python
from backend.repositories.interfaces.participante_interface import IParticipanteRepo
from backend.repositories.participante_repo import ParticipanteRepo
from backend.schemas.participante import ParticipanteResponse
from backend.core.exceptions import NotFoundException, ValidationException
from typing import List, Optional
import pandas as pd

class PresenceService:
    def __init__(self, repo: Optional[IParticipanteRepo] = None):
        """
        Initialize service with repository.
        If no repo provided, creates default implementation (for backward compatibility).
        """
        self.repo = repo if repo is not None else ParticipanteRepo()

    def listar_nomes(self) -> List[ParticipanteResponse]:
        """Lista participantes em ordem alfabética"""
        data = self.repo.listar_ordem_alfabetica()
        return [ParticipanteResponse(**p) for p in data]

    def listar_presentes(self) -> List[ParticipanteResponse]:
        """Lista apenas participantes presentes"""
        data = self.repo.listar_presentes()
        return [ParticipanteResponse(**p) for p in data]
    
    def marcar_presenca(self, user_id: int, mark: int | bool) -> bool:
        """Marca ou desmarca presença de um participante"""
        success = self.repo.marcar_presenca(user_id, int(mark))
        if not success:
            raise NotFoundException("Participante", user_id)
        return success
    
    def importar_excel(self, caminho_arquivo: str) -> int:
        """
        Importa participantes de arquivo Excel.
        Returns: número de participantes importados
        """
        try:
            df = pd.read_excel(caminho_arquivo)
        except Exception as e:
            raise ValidationException(f"Erro ao ler arquivo Excel: {str(e)}")

        if "Nome" not in df.columns:
            raise ValidationException("O arquivo precisa ter a coluna 'Nome'")

        nomes = [
            nome.strip()
            for nome in df["Nome"].dropna()
            if nome.strip()
        ]
        
        if not nomes:
            raise ValidationException("Nenhum nome válido encontrado no arquivo")
        
        self.repo.delete_participantes()
        self.repo.criar_participantes(nomes)
        
        return len(nomes)

    def delete_participantes(self) -> bool:
        """Deleta todos os participantes"""
        return self.repo.delete_participantes()
```

#### Step 3.2: Update Frontend to Use New Service (Backward Compatible)

The frontend code doesn't need to change because we made the repo parameter optional with a default value. The service still works exactly the same way when instantiated without arguments.

#### Step 3.3: Refactor Other Services

Apply the same pattern to `QuestionService` and `RankingService`:

```python
class QuestionService:
    def __init__(
        self, 
        q_repo: Optional[IQuestaoRepo] = None,
        r_repo: Optional[IRespostaRepo] = None
    ):
        self.q_repo = q_repo if q_repo is not None else QuestaoRepo()
        self.r_repo = r_repo if r_repo is not None else RespostaRepo()
    
    # Keep all existing methods, add type hints and error handling
```

## Phase 4: Add Async Support (Week 4-5)

### Goal: Prepare for FastAPI async endpoints

#### Step 4.1: Create Async Connection Handler

**src/backend/config/async_connection.py**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.core.config import settings
from typing import AsyncGenerator

class AsyncDBConnectionHandler:
    _engine = None
    _session_factory = None
    
    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            cls._engine = create_async_engine(
                settings.DATABASE_URL_ASYNC,
                echo=settings.DEBUG,
                future=True
            )
        return cls._engine
    
    @classmethod
    def get_session_factory(cls):
        if cls._session_factory is None:
            cls._session_factory = async_sessionmaker(
                cls.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )
        return cls._session_factory
    
    @classmethod
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Dependency for FastAPI"""
        session_factory = cls.get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
```

#### Step 4.2: Create Async Repository Implementations

**src/backend/repositories/async_participante_repo.py**
```python
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.entities.participante import Participante
from backend.repositories.interfaces.participante_interface import IParticipanteRepo
from typing import List, Optional

class AsyncParticipanteRepo(IParticipanteRepo):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def listar_ordem_alfabetica(self) -> List[dict]:
        result = await self.session.execute(
            select(Participante).order_by(Participante.nome)
        )
        participantes = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "nome": p.nome,
                "presente": p.presente
            }
            for p in participantes
        ]
    
    async def listar_presentes(self) -> List[dict]:
        result = await self.session.execute(
            select(Participante).where(Participante.presente == True)
        )
        participantes = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "nome": p.nome
            }
            for p in participantes
        ]
    
    async def marcar_presenca(self, user_id: int, mark: int) -> bool:
        presente = bool(mark)
        
        result = await self.session.execute(
            select(Participante).where(Participante.id == user_id)
        )
        participante = result.scalar_one_or_none()
        
        if not participante:
            return False
        
        participante.presente = presente
        return True
    
    # Implement other methods...
```

## Phase 5: Create API Layer (Week 5-6)

### Goal: Build FastAPI endpoints

#### Step 5.1: Create FastAPI App Structure

**src/backend/api/dependencies.py**
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.config.async_connection import AsyncDBConnectionHandler
from backend.repositories.async_participante_repo import AsyncParticipanteRepo
from backend.services.presence_service import PresenceService

async def get_db_session() -> AsyncSession:
    """Database session dependency"""
    async for session in AsyncDBConnectionHandler.get_session():
        yield session

def get_participante_repo(
    session: AsyncSession = Depends(get_db_session)
) -> AsyncParticipanteRepo:
    """Participante repository dependency"""
    return AsyncParticipanteRepo(session)

def get_presence_service(
    repo: AsyncParticipanteRepo = Depends(get_participante_repo)
) -> PresenceService:
    """Presence service dependency"""
    return PresenceService(repo)
```

#### Step 5.2: Create API Endpoints

**src/backend/api/v1/endpoints/participantes.py**
```python
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from backend.schemas.participante import (
    ParticipanteResponse, 
    ParticipanteCreate,
    ParticipanteUpdate
)
from backend.services.presence_service import PresenceService
from backend.api.dependencies import get_presence_service
from backend.core.exceptions import NotFoundException, ValidationException

router = APIRouter(prefix="/participantes", tags=["participantes"])

@router.get("/", response_model=List[ParticipanteResponse])
async def listar_participantes(
    service: PresenceService = Depends(get_presence_service)
):
    """Lista todos os participantes em ordem alfabética"""
    return service.listar_nomes()

@router.get("/presentes", response_model=List[ParticipanteResponse])
async def listar_presentes(
    service: PresenceService = Depends(get_presence_service)
):
    """Lista apenas participantes presentes"""
    return service.listar_presentes()

@router.patch("/{participante_id}/presenca")
async def marcar_presenca(
    participante_id: int,
    presente: bool,
    service: PresenceService = Depends(get_presence_service)
):
    """Marca ou desmarca presença de um participante"""
    try:
        service.marcar_presenca(participante_id, presente)
        return {"success": True, "message": "Presença atualizada"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message)

@router.post("/import")
async def importar_participantes(
    file: UploadFile = File(...),
    service: PresenceService = Depends(get_presence_service)
):
    """Importa lista de participantes de arquivo Excel"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Arquivo deve ser Excel (.xlsx ou .xls)"
        )
    
    # Save temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        count = service.importar_excel(tmp_path)
        return {
            "success": True,
            "message": f"{count} participantes importados"
        }
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=e.message)
    finally:
        import os
        os.unlink(tmp_path)
```

#### Step 5.3: Create Main FastAPI App

**src/api_main.py** (new file, separate from desktop app)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.api.v1.endpoints import participantes
from backend.core.exceptions import AppException
from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para gerenciamento de quiz/exam sessions"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

# Include routers
app.include_router(participantes.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Phase 6: Testing (Week 6-7)

### Goal: Ensure reliability with unit tests

#### Step 6.1: Setup Testing Infrastructure

Install pytest:
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

**tests/conftest.py**
```python
import pytest
from unittest.mock import Mock
from backend.repositories.participante_repo import ParticipanteRepo

@pytest.fixture
def mock_participante_repo():
    """Mock repository for testing"""
    repo = Mock(spec=ParticipanteRepo)
    repo.listar_ordem_alfabetica.return_value = [
        {"id": 1, "nome": "Alice", "presente": True},
        {"id": 2, "nome": "Bob", "presente": False}
    ]
    return repo
```

**tests/services/test_presence_service.py**
```python
import pytest
from backend.services.presence_service import PresenceService
from backend.core.exceptions import NotFoundException

def test_listar_nomes(mock_participante_repo):
    service = PresenceService(repo=mock_participante_repo)
    result = service.listar_nomes()
    
    assert len(result) == 2
    assert result[0].nome == "Alice"
    assert result[0].presente == True

def test_marcar_presenca_not_found(mock_participante_repo):
    mock_participante_repo.marcar_presenca.return_value = False
    service = PresenceService(repo=mock_participante_repo)
    
    with pytest.raises(NotFoundException):
        service.marcar_presenca(999, True)
```

## Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Foundation | 1-2 weeks | Pydantic schemas, core utilities |
| Phase 2: Interfaces | 1 week | Repository interfaces |
| Phase 3: DI Refactor | 1 week | Services with dependency injection |
| Phase 4: Async Support | 1 week | Async repositories and connection |
| Phase 5: API Layer | 1-2 weeks | FastAPI endpoints |
| Phase 6: Testing | 1 week | Unit tests, integration tests |

**Total: 6-8 weeks**

## Running Both Apps Simultaneously

During migration, you can run both:

```bash
# Terminal 1: Desktop app (existing)
python src/main.py

# Terminal 2: API server (new)
python src/api_main.py
# or
uvicorn src.api_main:app --reload
```

## Next Steps After Completion

1. Build Flutter frontend consuming the API
2. Add authentication/authorization
3. Deploy API to cloud (AWS, GCP, Azure)
4. Migrate from SQLite to PostgreSQL
5. Add caching layer (Redis)
6. Implement monitoring and logging
