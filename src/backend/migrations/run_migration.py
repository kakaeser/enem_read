"""
Migration runner script.
Run this script to execute the database migration from single-exam to multi-exam structure.

Usage:
    python src/backend/migrations/run_migration.py
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.migrations.single_to_multi_exam_migration import upgrade, MigrationError
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the migration"""
    print("\n" + "=" * 70)
    print("DATABASE MIGRATION: Single-Exam to Multi-Exam System")
    print("=" * 70)
    print("\nThis migration will:")
    print("  1. Create the new 'exams' table")
    print("  2. Add exam_id columns to existing tables")
    print("  3. Create a 'Legacy Exam' for existing data")
    print("  4. Associate all existing records with the Legacy Exam")
    print("  5. Transform response data (acertou -> marked_answer)")
    print("  6. Validate data integrity")
    print("\n⚠️  IMPORTANT: Backup your database before proceeding!")
    print("=" * 70)
    
    response = input("\nDo you want to proceed with the migration? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        return
    
    try:
        print("\nStarting migration...\n")
        upgrade()
        print("\n✓ Migration completed successfully!")
        print("\nYou can now:")
        print("  - Create new exams")
        print("  - Manage multiple exam sessions")
        print("  - View existing data under 'Legacy Exam'")
        
    except MigrationError as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n✗ Migration failed: {e}")
        print("\nPlease restore from backup and check the error logs.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n✗ Unexpected error: {e}")
        print("\nPlease restore from backup and check the error logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()
