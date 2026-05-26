# Database Migration: Single-Exam to Multi-Exam System

## Overview

This migration transforms the existing single-exam "Enem da Read" application into a multi-exam system with OCR capabilities. The migration preserves all existing data by creating a "Legacy Exam" and associating all current records with it.

## What This Migration Does

### 1. Schema Changes

#### New Table: `exams`
- `exam_id` (Primary Key)
- `exam_name` (String, 255 chars)
- `questions_numbers` (Integer)
- `symbolic_note` (Integer, default 1000)
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `status` (String: draft, in_progress, completed)

#### Modified Tables

**questoes (Questions)**
- Added: `exam_id` (Foreign Key to exams)
- Added: `question_correct_answer` (String, 10 chars) - stores A, B, C, D, E, etc.
- Added: Unique constraint on (exam_id, numero)
- Added: Index on exam_id

**participantes (Participants)**
- Added: `exam_id` (Foreign Key to exams)
- Added: `essay_points` (Float, default 0.0)
- Added: Index on exam_id

**resultados (Responses)**
- Added: `exam_id` (Foreign Key to exams)
- Added: `marked_answer` (String, 10 chars) - replaces acertou boolean
- Added: `confidence_score` (Float) - for OCR confidence
- Added: `manually_reviewed` (Boolean) - tracks manual review status
- Added: Index on exam_id
- Added: Index on user_id

### 2. Data Migration

1. **Legacy Exam Creation**: Creates a default exam named "Legacy Exam" with:
   - `questions_numbers`: Count of existing questions
   - `symbolic_note`: Value from Config.nota_simb (or 1000)
   - `status`: "completed"

2. **Data Association**: All existing records are associated with the Legacy Exam:
   - All questions → Legacy Exam
   - All participants → Legacy Exam
   - All responses → Legacy Exam

3. **Response Transformation**: 
   - `acertou=True` → `marked_answer='A'` (placeholder)
   - `acertou=False` → `marked_answer='B'` (placeholder)
   - Note: Actual marked answers are not available from old data

### 3. Validation

The migration validates:
- All questions have exam_id
- All participants have exam_id
- All responses have exam_id
- All responses have marked_answer
- Legacy Exam exists
- All foreign keys are valid

## Running the Migration

### Prerequisites

1. **Backup your database!**
   ```bash
   cp src/backend/database.db src/backend/database.db.backup
   ```

2. Ensure virtual environment is activated:
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

### Method 1: Using the Migration Runner (Recommended)

```bash
python src/backend/migrations/run_migration.py
```

This interactive script will:
- Show you what the migration will do
- Ask for confirmation
- Run the migration
- Display results

### Method 2: Direct Execution

```bash
python -m backend.migrations.single_to_multi_exam_migration
```

### Method 3: Programmatic

```python
from backend.migrations import upgrade

try:
    upgrade()
    print("Migration successful!")
except Exception as e:
    print(f"Migration failed: {e}")
```

## After Migration

### What You Can Do

1. **View Legacy Data**: All existing data is under "Legacy Exam"
2. **Create New Exams**: Use the Exam entity to create new exam sessions
3. **Multi-Exam Features**: Manage multiple independent exam sessions

### Example: Creating a New Exam

```python
from backend.entities.exam import Exam
from backend.config.connection import DBConnectionHandler
from datetime import datetime

with DBConnectionHandler() as db:
    new_exam = Exam(
        exam_name="Simulado ENEM 2024 - Matemática",
        questions_numbers=45,
        symbolic_note=1000,
        status="draft"
    )
    db.session.add(new_exam)
    db.session.commit()
    print(f"Created exam with ID: {new_exam.exam_id}")
```

## Rollback

**Important**: This migration does not include an automatic rollback function for safety reasons.

To rollback:
1. Stop the application
2. Restore from your database backup:
   ```bash
   cp src/backend/database.db.backup src/backend/database.db
   ```

## Troubleshooting

### Migration Fails with "Table already exists"

The migration checks if tables exist before creating them. If you see this error, the exams table may already exist. Check your database schema.

### Migration Fails with "Column already exists"

The migration checks if columns exist before adding them. This error suggests a partial migration was run. Restore from backup and try again.

### Validation Fails

If validation fails, the migration will report which check failed. Common issues:
- Orphaned records without exam_id
- Invalid foreign key references
- Missing required data

Check the error message and logs for details.

## Migration Log

The migration produces detailed logs showing:
- Each step being executed
- Number of records updated
- Validation results
- Any warnings or errors

Example output:
```
============================================================
Starting database migration: Single-Exam to Multi-Exam
============================================================
Step 1: Creating Exam table...
✓ Exam table created
Step 2: Creating Legacy Exam...
Legacy Exam created with exam_id=1, questions_numbers=45, symbolic_note=1000
✓ Legacy Exam created
Step 3: Adding exam_id columns...
Adding exam_id to questoes table...
Adding exam_id to participantes table...
Adding exam_id to resultados table...
✓ exam_id columns added
...
✓ Migration validation passed!
============================================================
Migration completed successfully!
============================================================
```

## Technical Details

### Database Compatibility

- **Development**: SQLite (file-based)
- **Production**: PostgreSQL recommended (better concurrency)

The migration uses SQLAlchemy, so it's database-agnostic. However, some SQL statements use SQLite syntax. For PostgreSQL, minor adjustments may be needed.

### Transaction Safety

The migration runs within a database transaction. If any step fails, all changes are rolled back automatically.

### Performance

Migration time depends on data volume:
- Small datasets (<1000 records): < 1 second
- Medium datasets (1000-10000 records): 1-5 seconds
- Large datasets (>10000 records): 5-30 seconds

## Support

If you encounter issues:
1. Check the migration logs
2. Verify database backup exists
3. Review the validation error messages
4. Restore from backup if needed
5. Report issues with full error logs

## Next Steps

After successful migration:
1. Test the application with legacy data
2. Create a new exam to test multi-exam functionality
3. Update application code to use new schema
4. Implement OCR features for answer key/sheet processing
