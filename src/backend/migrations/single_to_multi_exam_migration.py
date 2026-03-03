"""
Database Migration: Single-Exam to Multi-Exam System
Migrates existing single-exam data to multi-exam structure with backward compatibility.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey,
    UniqueConstraint, Index, text, inspect
)
from sqlalchemy.orm import Session
from backend.config.connection import DBConnectionHandler
from backend.config.base import Base
from backend.entities.exam import Exam
from backend.entities.participante import Participante
from backend.entities.questao import Questao
from backend.entities.resposta import Resposta
from backend.entities.config import Config
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Custom exception for migration errors"""
    pass


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(engine, table_name: str) -> bool:
    """Check if a table exists"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def create_legacy_exam(session: Session) -> Exam:
    """
    Create a default 'Legacy Exam' record for existing data.
    Retrieves configuration from Config table if available.
    """
    logger.info("Creating Legacy Exam record...")
    
    # Get existing config values
    config = session.query(Config).first()
    nota_max = config.nota_max if config else None
    nota_simb = config.nota_simb if config else 1000
    
    # Count existing questions to set questions_numbers
    from sqlalchemy import func
    questions_count = session.query(func.count(Questao.id)).scalar() or 0
    
    # Create legacy exam
    legacy_exam = Exam(
        exam_name="Legacy Exam",
        questions_numbers=max(questions_count, 1),  # At least 1
        symbolic_note=nota_simb,
        status="completed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    session.add(legacy_exam)
    session.flush()  # Get the exam_id
    
    logger.info(f"Legacy Exam created with exam_id={legacy_exam.exam_id}, "
                f"questions_numbers={legacy_exam.questions_numbers}, "
                f"symbolic_note={legacy_exam.symbolic_note}")
    
    return legacy_exam


def add_exam_id_columns(engine, session: Session):
    """Add exam_id columns to existing tables"""
    logger.info("Adding exam_id columns to existing tables...")
    
    # Add exam_id to questoes if not exists
    if not column_exists(engine, 'questoes', 'exam_id'):
        logger.info("Adding exam_id to questoes table...")
        session.execute(text(
            "ALTER TABLE questoes ADD COLUMN exam_id INTEGER"
        ))
    
    # Add exam_id to participantes if not exists
    if not column_exists(engine, 'participantes', 'exam_id'):
        logger.info("Adding exam_id to participantes table...")
        session.execute(text(
            "ALTER TABLE participantes ADD COLUMN exam_id INTEGER"
        ))
    
    # Add exam_id to resultados if not exists
    if not column_exists(engine, 'resultados', 'exam_id'):
        logger.info("Adding exam_id to resultados table...")
        session.execute(text(
            "ALTER TABLE resultados ADD COLUMN exam_id INTEGER"
        ))
    
    session.commit()


def add_new_columns(engine, session: Session):
    """Add new columns to existing tables"""
    logger.info("Adding new columns to existing tables...")
    
    # Add question_correct_answer to questoes
    if not column_exists(engine, 'questoes', 'question_correct_answer'):
        logger.info("Adding question_correct_answer to questoes table...")
        session.execute(text(
            "ALTER TABLE questoes ADD COLUMN question_correct_answer VARCHAR(10)"
        ))
    
    # Add marked_answer to resultados
    if not column_exists(engine, 'resultados', 'marked_answer'):
        logger.info("Adding marked_answer to resultados table...")
        session.execute(text(
            "ALTER TABLE resultados ADD COLUMN marked_answer VARCHAR(10)"
        ))
    
    # Add confidence_score to resultados
    if not column_exists(engine, 'resultados', 'confidence_score'):
        logger.info("Adding confidence_score to resultados table...")
        session.execute(text(
            "ALTER TABLE resultados ADD COLUMN confidence_score FLOAT"
        ))
    
    # Add manually_reviewed to resultados
    if not column_exists(engine, 'resultados', 'manually_reviewed'):
        logger.info("Adding manually_reviewed to resultados table...")
        session.execute(text(
            "ALTER TABLE resultados ADD COLUMN manually_reviewed BOOLEAN DEFAULT 0"
        ))
    
    # Add essay_points to participantes
    if not column_exists(engine, 'participantes', 'essay_points'):
        logger.info("Adding essay_points to participantes table...")
        session.execute(text(
            "ALTER TABLE participantes ADD COLUMN essay_points FLOAT DEFAULT 0.0"
        ))
    
    session.commit()


def populate_legacy_exam_ids(session: Session, legacy_exam_id: int):
    """Associate all existing records with the legacy exam"""
    logger.info(f"Associating existing records with legacy exam (exam_id={legacy_exam_id})...")
    
    # Update questoes
    questions_updated = session.execute(text(
        f"UPDATE questoes SET exam_id = {legacy_exam_id} WHERE exam_id IS NULL"
    )).rowcount
    logger.info(f"Updated {questions_updated} questions with legacy exam_id")
    
    # Update participantes
    participants_updated = session.execute(text(
        f"UPDATE participantes SET exam_id = {legacy_exam_id} WHERE exam_id IS NULL"
    )).rowcount
    logger.info(f"Updated {participants_updated} participants with legacy exam_id")
    
    # Update resultados
    responses_updated = session.execute(text(
        f"UPDATE resultados SET exam_id = {legacy_exam_id} WHERE exam_id IS NULL"
    )).rowcount
    logger.info(f"Updated {responses_updated} responses with legacy exam_id")
    
    session.commit()


def transform_responses(session: Session):
    """
    Transform existing Resposta records from acertou boolean to marked_answer string.
    This is a best-effort transformation since we don't have original marked answers.
    """
    logger.info("Transforming responses from acertou to marked_answer...")
    
    # For responses with acertou=True, set marked_answer to 'A' (placeholder)
    # For responses with acertou=False, set marked_answer to 'B' (placeholder)
    # This is a placeholder transformation - actual values are unknown
    
    correct_updated = session.execute(text(
        "UPDATE resultados SET marked_answer = 'A' WHERE acertou = 1 AND marked_answer IS NULL"
    )).rowcount
    logger.info(f"Set marked_answer='A' for {correct_updated} correct responses")
    
    incorrect_updated = session.execute(text(
        "UPDATE resultados SET marked_answer = 'B' WHERE acertou = 0 AND marked_answer IS NULL"
    )).rowcount
    logger.info(f"Set marked_answer='B' for {incorrect_updated} incorrect responses")
    
    session.commit()
    
    logger.warning("Note: marked_answer values are placeholders. "
                   "Actual marked answers from original data are not available.")


def validate_migration(session: Session) -> bool:
    """
    Validate data integrity after migration.
    Returns True if validation passes, raises MigrationError otherwise.
    """
    logger.info("Validating migration data integrity...")
    
    # Check 1: All questions have exam_id
    orphan_questions = session.execute(text(
        "SELECT COUNT(*) FROM questoes WHERE exam_id IS NULL"
    )).scalar()
    if orphan_questions > 0:
        raise MigrationError(f"Found {orphan_questions} questions without exam_id")
    logger.info("✓ All questions have exam_id")
    
    # Check 2: All participants have exam_id
    orphan_participants = session.execute(text(
        "SELECT COUNT(*) FROM participantes WHERE exam_id IS NULL"
    )).scalar()
    if orphan_participants > 0:
        raise MigrationError(f"Found {orphan_participants} participants without exam_id")
    logger.info("✓ All participants have exam_id")
    
    # Check 3: All responses have exam_id
    orphan_responses = session.execute(text(
        "SELECT COUNT(*) FROM resultados WHERE exam_id IS NULL"
    )).scalar()
    if orphan_responses > 0:
        raise MigrationError(f"Found {orphan_responses} responses without exam_id")
    logger.info("✓ All responses have exam_id")
    
    # Check 4: All responses have marked_answer
    responses_without_answer = session.execute(text(
        "SELECT COUNT(*) FROM resultados WHERE marked_answer IS NULL"
    )).scalar()
    if responses_without_answer > 0:
        raise MigrationError(f"Found {responses_without_answer} responses without marked_answer")
    logger.info("✓ All responses have marked_answer")
    
    # Check 5: Legacy exam exists
    legacy_exam_count = session.query(Exam).filter(Exam.exam_name == "Legacy Exam").count()
    if legacy_exam_count == 0:
        raise MigrationError("Legacy Exam not found")
    logger.info("✓ Legacy Exam exists")
    
    # Check 6: All foreign keys are valid
    invalid_question_fks = session.execute(text(
        """
        SELECT COUNT(*) FROM questoes q 
        WHERE NOT EXISTS (SELECT 1 FROM exams e WHERE e.exam_id = q.exam_id)
        """
    )).scalar()
    if invalid_question_fks > 0:
        raise MigrationError(f"Found {invalid_question_fks} questions with invalid exam_id")
    logger.info("✓ All question foreign keys are valid")
    
    invalid_participant_fks = session.execute(text(
        """
        SELECT COUNT(*) FROM participantes p 
        WHERE NOT EXISTS (SELECT 1 FROM exams e WHERE e.exam_id = p.exam_id)
        """
    )).scalar()
    if invalid_participant_fks > 0:
        raise MigrationError(f"Found {invalid_participant_fks} participants with invalid exam_id")
    logger.info("✓ All participant foreign keys are valid")
    
    invalid_response_fks = session.execute(text(
        """
        SELECT COUNT(*) FROM resultados r 
        WHERE NOT EXISTS (SELECT 1 FROM exams e WHERE e.exam_id = r.exam_id)
        """
    )).scalar()
    if invalid_response_fks > 0:
        raise MigrationError(f"Found {invalid_response_fks} responses with invalid exam_id")
    logger.info("✓ All response foreign keys are valid")
    
    logger.info("✓ Migration validation passed!")
    return True


def upgrade():
    """
    Execute the migration from single-exam to multi-exam structure.
    """
    logger.info("=" * 60)
    logger.info("Starting database migration: Single-Exam to Multi-Exam")
    logger.info("=" * 60)
    
    db_handler = DBConnectionHandler()
    engine = db_handler.get_engine()
    
    try:
        with db_handler as db:
            session = db.session
            
            # Step 1: Create Exam table if not exists
            logger.info("Step 1: Creating Exam table...")
            if not table_exists(engine, 'exams'):
                Base.metadata.tables['exams'].create(engine)
                logger.info("✓ Exam table created")
            else:
                logger.info("✓ Exam table already exists")
            
            # Step 2: Create legacy exam
            logger.info("Step 2: Creating Legacy Exam...")
            legacy_exam = create_legacy_exam(session)
            session.commit()
            
            # Step 3: Add exam_id columns to existing tables
            logger.info("Step 3: Adding exam_id columns...")
            add_exam_id_columns(engine, session)
            
            # Step 4: Add new columns (question_correct_answer, marked_answer, etc.)
            logger.info("Step 4: Adding new columns...")
            add_new_columns(engine, session)
            
            # Step 5: Populate exam_id with legacy exam ID
            logger.info("Step 5: Associating existing data with Legacy Exam...")
            populate_legacy_exam_ids(session, legacy_exam.exam_id)
            
            # Step 6: Transform responses (acertou -> marked_answer)
            logger.info("Step 6: Transforming response data...")
            transform_responses(session)
            
            # Step 7: Validate migration
            logger.info("Step 7: Validating migration...")
            validate_migration(session)
            
            logger.info("=" * 60)
            logger.info("Migration completed successfully!")
            logger.info("=" * 60)
            logger.info(f"Legacy Exam ID: {legacy_exam.exam_id}")
            logger.info("All existing data has been associated with the Legacy Exam.")
            logger.info("You can now create new exams and manage multiple exam sessions.")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        logger.error("Rolling back changes...")
        raise MigrationError(f"Migration failed: {str(e)}")


def downgrade():
    """
    Rollback migration (not implemented for safety).
    Manual rollback required by restoring database backup.
    """
    raise NotImplementedError(
        "Downgrade not implemented. "
        "Please restore from database backup if rollback is needed."
    )


if __name__ == "__main__":
    """
    Run migration directly from command line.
    Usage: python -m backend.migrations.001_single_to_multi_exam
    """
    try:
        upgrade()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        exit(1)
