"""
Fix PostgreSQL sequences that are out of sync
This script resets sequences to match the maximum ID in each table
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from sqlalchemy import text
from app.core.config import settings


def fix_sequence(db, table_name: str, sequence_name: str) -> bool:
    """
    Fix a PostgreSQL sequence by setting it to max(id) + 1
    """
    try:
        # Get the maximum ID currently in the table
        result = db.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}"))
        max_id = result.scalar() or 0
        
        # Reset the sequence to the next value after the max ID
        db.execute(text(f"SELECT setval('{sequence_name}', {max_id + 1}, false)"))
        db.commit()
        
        print(f"  ✓ Fixed {sequence_name}: set to {max_id + 1}")
        return True
    except Exception as e:
        db.rollback()
        print(f"  ✗ Failed to fix {sequence_name}: {str(e)}")
        return False


def fix_all_sequences():
    """Fix all sequences in the database"""
    print("=" * 60)
    print("GENIE OPS - Fix Database Sequences")
    print("=" * 60)
    print(f"\nDatabase URL: {settings.DATABASE_URL}")
    print("\nFixing sequences...\n")

    try:
        db = SessionLocal()
        
        # Fix sequences for all tables
        sequences = [
            ("saas", "saas_id_seq"),
            ("directories", "directories_id_seq"),
            ("submissions", "submissions_id_seq"),
        ]
        
        success_count = 0
        for table_name, sequence_name in sequences:
            print(f"Fixing {table_name}...")
            if fix_sequence(db, table_name, sequence_name):
                success_count += 1
        
        db.close()
        
        print(f"\n{'=' * 60}")
        print(f"Fixed {success_count}/{len(sequences)} sequences successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to database: {str(e)}")
        print("\nPlease check:")
        print("  1. PostgreSQL is running")
        print("  2. Database connection settings in config.py")
        print("  3. Database exists and is accessible")
        sys.exit(1)


if __name__ == "__main__":
    fix_all_sequences()
