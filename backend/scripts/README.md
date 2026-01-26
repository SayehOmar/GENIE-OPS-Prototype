# GENIE OPS - Utility Scripts

Command-line tools for processing submissions and maintaining the database.

## Quick Start

### Windows (Batch File)

Double-click `submit.bat` or run from command line:

```batch
cd backend
scripts\submit.bat
```

This will show an interactive menu with options to process submissions.

### Python CLI

Run directly with Python:

```bash
cd backend
python scripts/submit.py
```

## Usage

### Interactive Menu Mode

Run without arguments to get an interactive menu:

```bash
python scripts/submit.py
```

Menu options:
1. Process All Pending Submissions
2. Process Specific Submission (by ID)
3. Process Submissions for SaaS Product
4. Retry Failed Submissions
5. Show Workflow Status
6. Exit

### Command-Line Arguments

#### Process All Pending Submissions

```bash
# Process all pending
python scripts/submit.py --all

# Process with limit
python scripts/submit.py --all --limit 10
```

#### Process Specific Submission

```bash
python scripts/submit.py --submission 123
```

#### Process SaaS Submissions

```bash
python scripts/submit.py --saas 5
```

#### Retry Failed Submissions

```bash
# Retry failed submissions older than 24 hours (default)
python scripts/submit.py --retry-failed

# Retry failed submissions older than 48 hours
python scripts/submit.py --retry-failed 48
```

#### Show Status

```bash
python scripts/submit.py --status
```

## Examples

### Example 1: Process All Pending

```bash
python scripts/submit.py --all
```

Output:
```
📋 Found 5 pending submission(s)
============================================================

🔄 Processing submission 1...
   SaaS: My Awesome SaaS
   Directory: Product Hunt (https://producthunt.com/submit)
✅ Submission 1 completed successfully

🔄 Processing submission 2...
   ...
```

### Example 2: Process Specific SaaS

```bash
python scripts/submit.py --saas 3
```

### Example 3: Check Status

```bash
python scripts/submit.py --status
```

Output:
```
============================================================
📊 Workflow Status
============================================================
Pending:    5
Processing: 2
Failed:     1
Approved:   10
Total:      18
============================================================
```

## Integration with Workflow Manager

The CLI script works alongside the automatic workflow manager:

- **Workflow Manager**: Processes submissions automatically every 30 seconds (configurable)
- **CLI Script**: Processes submissions immediately on demand

Both use the same `WorkflowManager` and `SubmissionWorkflow` classes, so they share the same logic and error handling.

## Requirements

- Python 3.11+
- Virtual environment activated (or system Python)
- PostgreSQL database running
- Backend dependencies installed (`pip install -r requirements.txt`)

## Troubleshooting

### Database Connection Error

```
ERROR: Could not connect to database
```

**Solution**: Make sure PostgreSQL is running and `DATABASE_URL` in `backend/.env` is correct.

### No Pending Submissions

```
✓ No pending submissions found
```

**Solution**: Create submissions via the API or frontend first.

### Submission Fails

Check the error message in the output. Common issues:
- Directory URL is invalid
- Form structure changed
- CAPTCHA detected (requires manual intervention)
- Network timeout

## API Endpoints

The CLI script can also be used alongside API endpoints:

- `POST /api/jobs/process-all` - Process all pending
- `POST /api/jobs/process-saas/{saas_id}` - Process SaaS submissions
- `POST /api/jobs/process/{submission_id}` - Process specific submission
- `POST /api/jobs/batch-process` - Process multiple submissions
- `GET /api/jobs/progress/{submission_id}` - Get submission progress

## Progress Tracking

Submissions track progress through these states:

1. `queued` (0%) - Submission is queued
2. `analyzing_form` (20%) - Analyzing form structure
3. `filling_form` (50%) - Filling form fields
4. `submitting` (80%) - Submitting form
5. `completed` (100%) - Submission completed successfully

Failed submissions may show:
- `failed_retry` - Failed but will retry
- `failed` - Failed permanently
- `captcha_required` - CAPTCHA detected

## Database Maintenance

### Fix Database Sequences

If you encounter errors like "duplicate key value violates unique constraint" when creating new records, the PostgreSQL sequences may be out of sync. This can happen when data is inserted manually or through migrations.

**Fix all sequences:**
```bash
cd backend
python scripts/fix_sequences.py
```

This script will:
- Check all tables (saas, directories, submissions)
- Reset each sequence to match the maximum ID + 1
- Display success/failure status for each sequence

**Example output:**
```
============================================================
GENIE OPS - Fix Database Sequences
============================================================

Database URL: postgresql://postgres:postgres@localhost:5432/genie_ops

Fixing sequences...

Fixing saas...
  ✓ Fixed saas_id_seq: set to 5
Fixing directories...
  ✓ Fixed directories_id_seq: set to 3
Fixing submissions...
  ✓ Fixed submissions_id_seq: set to 12

============================================================
Fixed 3/3 sequences successfully!
============================================================
```

**Note:** The `create_directory` function now automatically fixes sequence issues when they occur, so this script is mainly for manual maintenance or bulk fixes.

## Notes

- The script uses the same database and workflow logic as the API
- Submissions are processed sequentially (one at a time) in CLI mode
- Progress is tracked in memory and available via API
- Screenshots are saved to `backend/storage/screenshots/`
- Form analysis reports are saved to `backend/test/reports/` (if using test form)
