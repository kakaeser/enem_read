# Enem da Read

> A desktop application for managing quiz/exam sessions with real-time attendance tracking, answer management, and automated ranking systems. Currently undergoing architectural refactoring for web deployment with FastAPI + Flutter.

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.2-green.svg)](https://github.com/TomSchimansky/CustomTkinter)

## 🎯 Overview

Educational management tool designed for instructors to conduct quiz sessions with features including:

- **Attendance Management** - Track student presence with visual interface
- **Question/Answer System** - Manage individual student responses with weighted scoring
- **Real-time Ranking** - Automated leaderboard generation based on performance
- **Excel Integration** - Import/export participant lists and rankings
- **Dark-themed UI** - Modern interface built with CustomTkinter

## 🏗️ Architecture

### Current Stack (Desktop)

```
Python 3.x + CustomTkinter + SQLAlchemy + SQLite
```

**Layered Architecture:**
```
Frontend (CustomTkinter GUI)
    ↓
Services (Business Logic)
    ↓
Repositories (Data Access)
    ↓
Entities (SQLAlchemy ORM)
    ↓
SQLite Database
```

### Target Stack (Web - In Progress)

```
FastAPI + Flutter + PostgreSQL
```

**Modern Architecture:**
```
Flutter Frontend
    ↓
FastAPI REST API (with JWT Auth)
    ↓
Services (Dependency Injection)
    ↓
Repository Interfaces (SOLID Principles)
    ↓
Async SQLAlchemy ORM
    ↓
PostgreSQL Database
```

## 🚀 Quick Start

### Prerequisites

- Python 3.x
- pip

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/enem-da-read.git
cd enem-da-read

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Desktop version
python src/main.py
```

## 📁 Project Structure

```
src/
├── backend/
│   ├── config/          # Database configuration
│   ├── entities/        # SQLAlchemy ORM models
│   ├── repositories/    # Data access layer (Repository pattern)
│   ├── services/        # Business logic layer
│   └── seed/            # Database seeding
├── frontend/            # CustomTkinter GUI components
└── main.py             # Application entry point
```

## 🔄 Migration Roadmap

Currently refactoring from desktop to web architecture following a **6-8 week phased approach**:

### ✅ Phase 1: Foundation (Weeks 1-2)
- Add Pydantic schemas for type safety
- Implement core utilities and exception handling
- Create configuration management with environment variables

### 🔄 Phase 2: Decoupling (Weeks 2-3)
- Create repository interfaces (SOLID principles)
- Implement dependency injection in services
- Maintain backward compatibility with desktop app

### 📋 Phase 3: Async Support (Weeks 4-5)
- Migrate to async SQLAlchemy
- Create async repository implementations
- Prepare for FastAPI integration

### 📋 Phase 4: API Layer (Weeks 5-6)
- Build FastAPI REST endpoints
- Implement JWT authentication
- Add CORS and middleware configuration

### 📋 Phase 5: Testing & Deployment (Weeks 6-7)
- Unit tests with pytest
- Integration tests for API endpoints
- CI/CD pipeline setup

## 🛠️ Key Technologies

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Language** | Python 3.x | Core development |
| **GUI** | CustomTkinter 5.2 | Desktop interface |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Database** | SQLite → PostgreSQL | Data persistence |
| **Data Processing** | Pandas 3.0 | Excel operations |
| **API** | FastAPI (planned) | REST API framework |
| **Frontend** | Flutter (planned) | Cross-platform UI |
| **Validation** | Pydantic (in progress) | Data validation |

## 🎨 Features

### Current Features
- ✅ Participant attendance tracking
- ✅ Question management with weighted scoring
- ✅ Automated ranking calculation
- ✅ Excel import/export
- ✅ Dark mode interface

### Planned Features
- 🔄 RESTful API with FastAPI
- 🔄 JWT authentication & authorization
- 🔄 Real-time updates via WebSocket
- 🔄 Multi-platform support (Web, iOS, Android)
- 🔄 PostgreSQL database with connection pooling
- 🔄 Redis caching layer
- 🔄 Comprehensive API documentation

## 📊 Database Schema

**Core Entities:**
- `Participante` - Student information and presence status
- `Questao` - Questions with number and weight
- `Resposta` - Student answers with correctness flag
- `Config` - System configuration for scoring

**Relationships:**
- One-to-Many: Participante → Resposta
- One-to-Many: Questao → Resposta
- Unique Constraint: (user_id, quest_id) per answer

## 🧪 Development Principles

Following **SOLID principles** and **Clean Architecture**:

- **Dependency Inversion** - Services depend on repository interfaces
- **Single Responsibility** - Each layer has one clear purpose
- **Repository Pattern** - Abstracted data access
- **Dependency Injection** - Testable, flexible services
- **Type Safety** - Pydantic schemas for validation

## 📝 Code Quality

```python
# Example: Service with Dependency Injection
class PresenceService:
    def __init__(self, repo: IParticipanteRepo):
        self.repo = repo
    
    def listar_nomes(self) -> List[ParticipanteResponse]:
        data = self.repo.listar_ordem_alfabetica()
        return [ParticipanteResponse(**p) for p in data]
```

## 🤝 Contributing

This project is currently under active refactoring. Contributions welcome after Phase 4 completion.

## 📄 License

[Add your license here]

## 👤 Author

**kakaeser**

## 🔗 Links

- [Documentation](./docs) *(coming soon)*
- [API Documentation](./api-docs) *(coming soon)*
- [Change Log](./CHANGELOG.md) *(coming soon)*

---

**Status:** 🔄 Active Development - Desktop version functional, web migration in progress

**Last Updated:** March 2026
