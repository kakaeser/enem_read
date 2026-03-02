# Technology Stack

## Core Technologies

- **Language**: Python 3.x
- **GUI Framework**: CustomTkinter (5.2.2) - Modern UI library built on tkinter
- **Database**: SQLite with SQLAlchemy (2.0.46) ORM
- **Data Processing**: Pandas (3.0.0) for Excel operations

## Key Libraries

- **customtkinter**: Modern, customizable tkinter widgets with dark mode support
- **SQLAlchemy**: Database ORM for entity management and queries
- **pandas**: Excel file import/export operations
- **openpyxl**: Excel file format support
- **numpy**: Data processing support

## Development Setup

### Installation

```bash
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
# From project root
python src/main.py
```

### Database Initialization

The database is automatically initialized on first run via `backend.config.db_init.init_db()`. The SQLite database file is created at `src/backend/database.db`.

## Build Notes

- No compilation required (Python interpreted)
- Virtual environment (`.venv`) should be activated before running
- Database schema is managed through SQLAlchemy models
