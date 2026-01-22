"""
GENIE OPS - Submission Processing CLI
Standalone script for processing submissions immediately
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.db.crud import (
    get_submissions,
    get_submission_by_id,
    get_saas_by_id,
    get_directory_by_id,
    get_directories,
    get_submission_by_saas_directory,
    create_submission,
    update_submission,
)
from app.db.models import SubmissionUpdate, SubmissionCreate
from app.workflow.submitter import SubmissionWorkflow
from app.workflow.manager import WorkflowManager
from app.utils.logger import logger
from app.core.config import settings


class SubmissionCLI:
    """CLI interface for processing submissions"""

    def __init__(self):
        self.workflow = SubmissionWorkflow()
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0

    async def process_all_pending(self, limit: Optional[int] = None):
        """Process all pending submissions"""
        db = SessionLocal()
        try:
            pending = get_submissions(db, status="pending")
            if limit:
                pending = pending[:limit]

            if not pending:
                print("✓ No pending submissions found")
                return

            print(f"\n📋 Found {len(pending)} pending submission(s)")
            print("=" * 60)

            for submission in pending:
                await self._process_single_submission(submission.id, db)

            self._print_summary()
        finally:
            db.close()

    async def process_submission(self, submission_id: int):
        """Process a specific submission by ID"""
        db = SessionLocal()
        try:
            submission = get_submission_by_id(db, submission_id)
            if not submission:
                print(f"❌ Submission {submission_id} not found")
                return

            if submission.status not in ["pending", "failed"]:
                print(
                    f"⚠️  Submission {submission_id} is not pending or failed "
                    f"(status: {submission.status})"
                )
                return

            await self._process_single_submission(submission_id, db)
            self._print_summary()
        finally:
            db.close()

    async def process_saas_submissions(self, saas_id: int):
        """Process all submissions for a specific SaaS product"""
        db = SessionLocal()
        try:
            saas = get_saas_by_id(db, saas_id)
            if not saas:
                print(f"❌ SaaS product {saas_id} not found")
                return

            submissions = get_submissions(db, saas_id=saas_id, status="pending")
            if not submissions:
                print(f"✓ No pending submissions found for SaaS: {saas.name}")
                return

            print(
                f"\n📋 Found {len(submissions)} pending submission(s) for: {saas.name}"
            )
            print("=" * 60)

            for submission in submissions:
                await self._process_single_submission(submission.id, db)

            self._print_summary()
        finally:
            db.close()

    async def retry_failed(self, max_age_hours: int = 24):
        """Retry failed submissions older than max_age_hours"""
        from datetime import timedelta

        db = SessionLocal()
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            all_failed = get_submissions(db, status="failed")

            failed_to_retry = [
                s
                for s in all_failed
                if s.updated_at
                and s.updated_at < cutoff_time
                and s.retry_count < settings.WORKFLOW_MAX_RETRIES
            ]

            if not failed_to_retry:
                print(f"✓ No failed submissions found older than {max_age_hours} hours")
                return

            print(
                f"\n📋 Found {len(failed_to_retry)} failed submission(s) to retry "
                f"(older than {max_age_hours} hours)"
            )
            print("=" * 60)

            # Reset status to pending
            for submission in failed_to_retry:
                update_submission(
                    db,
                    submission.id,
                    SubmissionUpdate(status="pending", error_message=None),
                )
                print(f"🔄 Queued submission {submission.id} for retry")

            # Process them
            for submission in failed_to_retry:
                await self._process_single_submission(submission.id, db)

            self._print_summary()
        finally:
            db.close()

    async def _process_single_submission(self, submission_id: int, db):
        """Process a single submission and update counters"""
        try:
            submission = get_submission_by_id(db, submission_id)
            if not submission:
                print(f"❌ Submission {submission_id} not found")
                return

            saas = get_saas_by_id(db, submission.saas_id)
            directory = get_directory_by_id(db, submission.directory_id)

            if not saas or not directory:
                print(f"❌ Missing data for submission {submission_id}")
                return

            print(f"\n🔄 Processing submission {submission_id}...")
            print(f"   SaaS: {saas.name}")
            print(f"   Directory: {directory.name} ({directory.url})")

            # Prepare SaaS data
            saas_data = {
                "name": saas.name,
                "url": saas.url,
                "contact_email": saas.contact_email,
                "description": saas.description or "",
                "category": saas.category or "",
                "logo_path": saas.logo_path or "",
            }

            # Update status to processing
            update_submission(db, submission_id, SubmissionUpdate(status="submitted"))
            db.commit()

            # Process submission
            result = await self.workflow.submit_to_directory(
                directory_url=directory.url, saas_data=saas_data
            )

            # Update based on result
            status = result.get("status", "failed")
            if status == "success":
                update_submission(
                    db,
                    submission_id,
                    SubmissionUpdate(
                        status="submitted",
                        submitted_at=datetime.now(),
                        form_data=str(result.get("form_structure", {})),
                    ),
                )
                print(f"✅ Submission {submission_id} completed successfully")
                self.success_count += 1
            else:
                error_msg = result.get("message", "Unknown error")
                update_submission(
                    db,
                    submission_id,
                    SubmissionUpdate(
                        status="failed",
                        error_message=error_msg,
                        form_data=str(result.get("form_structure", {})),
                    ),
                )
                print(f"❌ Submission {submission_id} failed: {error_msg}")
                self.failed_count += 1

            db.commit()
            self.processed_count += 1

        except Exception as e:
            logger.error(
                f"Error processing submission {submission_id}: {e}", exc_info=True
            )
            print(f"❌ Error processing submission {submission_id}: {str(e)}")
            try:
                update_submission(
                    db,
                    submission_id,
                    SubmissionUpdate(status="failed", error_message=str(e)),
                )
                db.commit()
            except:
                pass
            self.failed_count += 1
            self.processed_count += 1

    def _print_summary(self):
        """Print processing summary"""
        print("\n" + "=" * 60)
        print("📊 Processing Summary")
        print("=" * 60)
        print(f"Total Processed: {self.processed_count}")
        print(f"✅ Successful: {self.success_count}")
        print(f"❌ Failed: {self.failed_count}")
        if self.processed_count > 0:
            success_rate = (self.success_count / self.processed_count) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        print("=" * 60)

    def show_status(self):
        """Show current workflow status"""
        db = SessionLocal()
        try:
            pending = get_submissions(db, status="pending")
            submitted = get_submissions(db, status="submitted")
            failed = get_submissions(db, status="failed")
            approved = get_submissions(db, status="approved")

            print("\n" + "=" * 60)
            print("📊 Workflow Status")
            print("=" * 60)
            print(f"Pending:    {len(pending)}")
            print(f"Processing: {len(submitted)}")
            print(f"Failed:     {len(failed)}")
            print(f"Approved:   {len(approved)}")
            print(
                f"Total:      {len(pending) + len(submitted) + len(failed) + len(approved)}"
            )
            print("=" * 60)

            if pending:
                print("\n📋 Pending Submissions:")
                for sub in pending[:10]:  # Show first 10
                    saas = get_saas_by_id(db, sub.saas_id)
                    directory = get_directory_by_id(db, sub.directory_id)
                    saas_name = saas.name if saas else f"ID:{sub.saas_id}"
                    dir_name = directory.name if directory else f"ID:{sub.directory_id}"
                    print(f"  - ID {sub.id}: {saas_name} → {dir_name}")
                if len(pending) > 10:
                    print(f"  ... and {len(pending) - 10} more")

        finally:
            db.close()


async def interactive_menu():
    """Interactive menu mode"""
    cli = SubmissionCLI()

    while True:
        print("\n" + "=" * 60)
        print("GENIE OPS - Submission Processor")
        print("=" * 60)
        print("1. Create Submission Job (Link SaaS to Directories)")
        print("2. Process All Pending Submissions")
        print("3. Process Specific Submission (by ID)")
        print("4. Process Submissions for SaaS Product")
        print("5. Retry Failed Submissions")
        print("6. Show Workflow Status")
        print("7. Exit")
        print("=" * 60)

        choice = input("\nEnter choice (1-7): ").strip()

        if choice == "1":
            saas_id = input("Enter SaaS product ID: ").strip()
            if not saas_id.isdigit():
                print("[ERROR] Invalid SaaS ID")
            else:
                dir_input = input(
                    "Enter directory IDs (comma-separated, or press Enter for all): "
                ).strip()
                if dir_input:
                    try:
                        directory_ids = [int(d.strip()) for d in dir_input.split(",")]
                    except ValueError:
                        print("[ERROR] Invalid directory IDs format")
                        directory_ids = None
                else:
                    directory_ids = None
                cli.create_submission_job(int(saas_id), directory_ids)

        elif choice == "2":
            limit_input = input(
                "Limit number of submissions? (Enter number or press Enter for all): "
            ).strip()
            limit = int(limit_input) if limit_input.isdigit() else None
            await cli.process_all_pending(limit=limit)

        elif choice == "3":
            submission_id = input("Enter submission ID: ").strip()
            if submission_id.isdigit():
                await cli.process_submission(int(submission_id))
            else:
                print("[ERROR] Invalid submission ID")

        elif choice == "4":
            saas_id = input("Enter SaaS product ID: ").strip()
            if saas_id.isdigit():
                await cli.process_saas_submissions(int(saas_id))
            else:
                print("[ERROR] Invalid SaaS ID")

        elif choice == "5":
            hours_input = input(
                "Retry submissions older than (hours, default 24): "
            ).strip()
            hours = int(hours_input) if hours_input.isdigit() else 24
            await cli.retry_failed(max_age_hours=hours)

        elif choice == "6":
            cli.show_status()

        elif choice == "7":
            print("\nGoodbye!")
            break

        else:
            print("[ERROR] Invalid choice. Please enter 1-7.")

        input("\nPress Enter to continue...")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="GENIE OPS - Submission Processing CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/submit.py                    # Interactive menu
  python scripts/submit.py --all              # Process all pending
  python scripts/submit.py --submission 123    # Process specific submission
  python scripts/submit.py --saas 5           # Process SaaS submissions
  python scripts/submit.py --retry-failed 24   # Retry failed (24h old)
  python scripts/submit.py --status            # Show status
        """,
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all pending submissions",
    )
    parser.add_argument(
        "--submission",
        type=int,
        help="Process specific submission by ID",
    )
    parser.add_argument(
        "--saas",
        type=int,
        help="Process all submissions for SaaS product ID",
    )
    parser.add_argument(
        "--retry-failed",
        type=int,
        metavar="HOURS",
        help="Retry failed submissions older than HOURS (default: 24)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show workflow status",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of submissions to process (with --all)",
    )
    parser.add_argument(
        "--create-job",
        type=int,
        metavar="SAAS_ID",
        help="Create submission job for SaaS ID (links to all directories or specified ones)",
    )
    parser.add_argument(
        "--directories",
        type=str,
        metavar="IDS",
        help="Comma-separated directory IDs (use with --create-job)",
    )

    args = parser.parse_args()

    cli = SubmissionCLI()

    try:
        if args.create_job:
            directory_ids = None
            if args.directories:
                try:
                    directory_ids = [
                        int(d.strip()) for d in args.directories.split(",")
                    ]
                except ValueError:
                    print(
                        "[ERROR] Invalid directory IDs format. Use comma-separated numbers."
                    )
                    sys.exit(1)
            cli.create_submission_job(args.create_job, directory_ids)
        elif args.status:
            cli.show_status()
        elif args.all:
            await cli.process_all_pending(limit=args.limit)
        elif args.submission:
            await cli.process_submission(args.submission)
        elif args.saas:
            await cli.process_saas_submissions(args.saas)
        elif args.retry_failed is not None:
            await cli.retry_failed(max_age_hours=args.retry_failed or 24)
        else:
            # No arguments - run interactive menu
            await interactive_menu()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"CLI error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
