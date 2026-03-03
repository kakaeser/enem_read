"""
Database migrations package for multi-exam OCR system.
"""

from .single_to_multi_exam_migration import upgrade, downgrade

__all__ = ['upgrade', 'downgrade']
