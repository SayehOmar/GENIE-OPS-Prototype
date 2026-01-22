"""
Quick database verification script
Checks connection and displays existing data
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.crud import get_saas_list, get_directories, get_submissions
from app.core.config import settings


def verify_database():
    """Verify database connection and show existing data"""
    print("=" * 60)
    print("GENIE OPS - Database Verification")
    print("=" * 60)
    print(f"\nDatabase URL: {settings.DATABASE_URL}")
    print("\nTesting connection...")

    try:
        db = SessionLocal()
        print("[OK] Database connection successful!")

        # Get SaaS products
        saas_list = get_saas_list(db)
        print(f"\nSaaS Products: {len(saas_list)}")
        for saas in saas_list:
            print(f"   - ID {saas.id}: {saas.name}")
            print(f"     URL: {saas.url}")
            print(f"     Category: {saas.category or 'N/A'}")
            print(f"     Email: {saas.contact_email}")

        # Get Directories
        directories = get_directories(db)
        print(f"\nDirectories: {len(directories)}")
        for directory in directories:
            print(f"   - ID {directory.id}: {directory.name}")
            print(f"     URL: {directory.url}")

        # Get Submissions
        all_submissions = get_submissions(db)
        print(f"\nSubmissions: {len(all_submissions)}")

        status_counts = {"pending": 0, "submitted": 0, "approved": 0, "failed": 0}
        for submission in all_submissions:
            status_counts[submission.status] = (
                status_counts.get(submission.status, 0) + 1
            )

        print(f"   - Pending: {status_counts['pending']}")
        print(f"   - Submitted: {status_counts['submitted']}")
        print(f"   - Approved: {status_counts['approved']}")
        print(f"   - Failed: {status_counts['failed']}")

        if all_submissions:
            print(f"\n   Recent submissions:")
            for sub in all_submissions[:5]:
                saas = next((s for s in saas_list if s.id == sub.saas_id), None)
                directory = next(
                    (d for d in directories if d.id == sub.directory_id), None
                )
                saas_name = saas.name if saas else f"ID:{sub.saas_id}"
                dir_name = directory.name if directory else f"ID:{sub.directory_id}"
                print(f"     - ID {sub.id}: {saas_name} -> {dir_name} [{sub.status}]")

        db.close()
        print("\n[OK] Database verification complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check DATABASE_URL in backend/.env file")
        print("3. Verify database 'genie-ops-prototype' exists")
        print("4. Check username/password are correct")
        sys.exit(1)


if __name__ == "__main__":
    verify_database()
