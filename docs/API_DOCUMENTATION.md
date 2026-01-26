# GENIE-OPS API Documentation

**Base URL:** `http://localhost:8000`  
**API Version:** 1.0.0

---

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [SaaS Products](#saas-products)
4. [Directories](#directories)
5. [Submissions](#submissions)
6. [Jobs & Workflow](#jobs--workflow)
7. [Testing](#testing)
8. [Error Responses](#error-responses)

---

## Authentication

### POST `/api/auth/login`

Authenticate and receive an access token.

**Rate Limit:** 10 requests/minute

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### POST `/api/auth/logout`

Logout and invalidate the current session.

**Rate Limit:** 10 requests/minute

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

---

## Rate Limiting

All API endpoints are rate-limited to prevent abuse. Rate limits vary by endpoint type:

- **Default:** 100 requests/minute
- **Authentication:** 10 requests/minute
- **Submissions:** 30 requests/minute
- **Jobs:** 20 requests/minute
- **Statistics:** 60 requests/minute
- **Health Checks:** 200 requests/minute

When a rate limit is exceeded, the API returns:
- **Status Code:** 429 Too Many Requests
- **Headers:**
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time when limit resets

**Example Response:**
```json
{
  "error": "Rate limit exceeded: 30 per 1 minute"
}
```

---

## SaaS Products

### GET `/api/saas`

List all SaaS products.

**Rate Limit:** 100 requests/minute

**Response:**
```json
[
  {
    "id": 1,
    "name": "My SaaS",
    "url": "https://example.com",
    "description": "Description",
    "category": "Productivity",
    "contact_email": "contact@example.com",
    "logo_path": "/path/to/logo.png",
    "created_at": "2026-01-25T00:00:00Z",
    "updated_at": "2026-01-25T00:00:00Z"
  }
]
```

### GET `/api/saas/{saas_id}`

Get a specific SaaS product by ID.

**Rate Limit:** 100 requests/minute

**Response:**
```json
{
  "id": 1,
  "name": "My SaaS",
  "url": "https://example.com",
  "description": "Description",
  "category": "Productivity",
  "contact_email": "contact@example.com",
  "logo_path": "/path/to/logo.png",
  "created_at": "2026-01-25T00:00:00Z",
  "updated_at": "2026-01-25T00:00:00Z"
}
```

### POST `/api/saas`

Create a new SaaS product.

**Rate Limit:** 30 requests/minute

**Request Body:**
```json
{
  "name": "My SaaS",
  "url": "https://example.com",
  "description": "Description",
  "category": "Productivity",
  "contact_email": "contact@example.com",
  "logo_path": "/path/to/logo.png"
}
```

**Response:** Created SaaS object (same structure as GET)

### PUT `/api/saas/{saas_id}`

Update an existing SaaS product.

**Rate Limit:** 30 requests/minute

**Request Body:** (All fields optional)
```json
{
  "name": "Updated Name",
  "url": "https://updated.com",
  "description": "Updated description",
  "category": "Updated Category",
  "contact_email": "new@example.com",
  "logo_path": "/new/path.png"
}
```

**Response:** Updated SaaS object

### DELETE `/api/saas/{saas_id}`

Delete a SaaS product.

**Rate Limit:** 30 requests/minute

**Response:**
```json
{
  "message": "SaaS product deleted successfully"
}
```

---

## Directories

### GET `/api/directories`

List all directories.

**Rate Limit:** 100 requests/minute

**Response:**
```json
[
  {
    "id": 1,
    "name": "Directory Name",
    "url": "https://directory.com/submit",
    "description": "Directory description",
    "created_at": "2026-01-25T00:00:00Z"
  }
]
```

### GET `/api/directories/{directory_id}`

Get a specific directory by ID.

**Rate Limit:** 100 requests/minute

**Response:** Directory object (same structure as list)

### POST `/api/directories`

Create a new directory.

**Rate Limit:** 30 requests/minute

**Request Body:**
```json
{
  "name": "Directory Name",
  "url": "https://directory.com/submit",
  "description": "Directory description"
}
```

**Response:** Created directory object

### PUT `/api/directories/{directory_id}`

Update an existing directory.

**Rate Limit:** 30 requests/minute

**Request Body:** (All fields optional)
```json
{
  "name": "Updated Name",
  "url": "https://updated.com",
  "description": "Updated description"
}
```

**Response:** Updated directory object

### DELETE `/api/directories/{directory_id}`

Delete a directory.

**Rate Limit:** 30 requests/minute

**Response:**
```json
{
  "message": "Directory deleted successfully"
}
```

---

## Submissions

### GET `/api/submissions`

List all submissions, optionally filtered.

**Rate Limit:** 30 requests/minute

**Query Parameters:**
- `saas_id` (optional): Filter by SaaS product ID
- `directory_id` (optional): Filter by directory ID

**Response:**
```json
[
  {
    "id": 1,
    "saas_id": 1,
    "directory_id": 1,
    "status": "submitted",
    "submitted_at": "2026-01-25T00:00:00Z",
    "error_message": null,
    "form_data": "{\"fields_filled\": 4, \"total_fields\": 4}",
    "retry_count": 0,
    "created_at": "2026-01-25T00:00:00Z",
    "updated_at": "2026-01-25T00:00:00Z"
  }
]
```

### GET `/api/submissions/{submission_id}`

Get a specific submission by ID.

**Rate Limit:** 30 requests/minute

**Response:** Submission object (same structure as list)

### POST `/api/submissions`

Create a new submission record.

**Rate Limit:** 30 requests/minute

**Request Body:**
```json
{
  "saas_id": 1,
  "directory_id": 1,
  "status": "pending",
  "form_data": null
}
```

**Response:** Created submission object

### PUT `/api/submissions/{submission_id}`

Update an existing submission.

**Rate Limit:** 30 requests/minute

**Request Body:** (All fields optional)
```json
{
  "status": "submitted",
  "submitted_at": "2026-01-25T00:00:00Z",
  "error_message": null,
  "form_data": "{\"fields_filled\": 4}",
  "retry_count": 0
}
```

**Response:** Updated submission object

### DELETE `/api/submissions/{submission_id}`

Delete a submission.

**Rate Limit:** 30 requests/minute

**Response:**
```json
{
  "message": "Submission deleted successfully"
}
```

### GET `/api/submissions/stats/summary`

Get submission statistics.

**Rate Limit:** 60 requests/minute

**Query Parameters:**
- `saas_id` (optional): Filter statistics by SaaS product ID

**Response:**
```json
{
  "total": 100,
  "pending": 10,
  "processing": 2,
  "submitted": 60,
  "approved": 20,
  "failed": 10,
  "success_rate": 80.0,
  "by_status": {
    "pending": 10,
    "submitted": 60,
    "approved": 20,
    "failed": 10,
    "processing": 2
  }
}
```

### POST `/api/submissions/{submission_id}/retry`

Retry a failed or pending submission.

Resets the submission status to "pending" and resets auto-retry stop count.
If status was auto_retry_failed_{x}, it resets to "pending" and clears the stop count.

**Rate Limit:** 30 requests/minute

**Response:**
```json
{
  "message": "Submission queued for retry (auto-retry stop count reset)",
  "submission": {
    "id": 1,
    "status": "pending",
    "retry_count": 1,
    ...
  },
  "retry_count": 1
}
```

### POST `/api/submissions/{submission_id}/stop-retry`

Stop automatic retry for a failed submission.

Sets status to auto_retry_failed_{x} where x increments from 1 to 5.
When x reaches 5, status becomes "failed" permanently.
This prevents the workflow manager from automatically retrying this submission.

**Rate Limit:** 30 requests/minute

**Response:**
```json
{
  "message": "Auto-retry stopped (stop count: 1/5)",
  "submission": {
    "id": 1,
    "status": "auto_retry_failed_1",
    "error_message": "Auto-retry stopped by user (stop count: 1/5)",
    ...
  },
  "auto_retry_stop_count": 1
}
```

---

## Jobs & Workflow

### POST `/api/jobs/start-submission`

Start a submission job for a SaaS product across multiple directories.

**Rate Limit:** 20 requests/minute

**Request Body:**
```json
{
  "saas_id": 1,
  "directory_ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "message": "Submission job started. 3 submissions queued.",
  "submissions_created": 3,
  "submission_ids": [1, 2, 3]
}
```

### POST `/api/jobs/process/{submission_id}`

Manually trigger processing for a specific submission.

**Rate Limit:** 20 requests/minute

**Response:**
```json
{
  "message": "Submission processing started",
  "submission_id": 1
}
```

### GET `/api/jobs/workflow/status`

Get current workflow manager status.

**Rate Limit:** 60 requests/minute

**Response:**
```json
{
  "is_running": true,
  "max_concurrent": 1,
  "batch_size": 10,
  "processing_interval": 30,
  "active_tasks": 2,
  "active_submission_ids": [1, 2],
  "total_tracked_tasks": 5,
  "active_submissions": [
    {
      "submission_id": 1,
      "saas_id": 1,
      "directory_id": 1,
      "status": "filling_form",
      "progress": 50,
      "message": "Filling form fields with SaaS data",
      "started_at": "2026-01-25T00:00:00Z",
      "retry_count": 0
    }
  ],
  "queue_length": 3
}
```

### POST `/api/jobs/workflow/start`

Start the workflow manager (enable automatic processing).

**Rate Limit:** 20 requests/minute

**Response:**
```json
{
  "message": "Workflow manager started",
  "status": {
    "is_running": true,
    "active_tasks": 0,
    "max_concurrent": 1,
    ...
  }
}
```

### POST `/api/jobs/workflow/stop`

Stop the workflow manager (disable automatic processing).

**Rate Limit:** 20 requests/minute

**Response:**
```json
{
  "message": "Workflow manager stopped",
  "status": {
    "is_running": false,
    "active_tasks": 0,
    ...
  }
}
```

### POST `/api/jobs/workflow/process-pending`

Manually trigger processing of all pending submissions.

**Rate Limit:** 20 requests/minute

**Response:**
```json
{
  "message": "Processing triggered",
  "status": {
    "is_running": true,
    "active_tasks": 5,
    ...
  }
}
```

### POST `/api/jobs/workflow/retry-failed`

Retry failed submissions older than specified hours.

**Rate Limit:** 20 requests/minute

**Query Parameters:**
- `max_age_hours` (optional, default: 24): Maximum age in hours

**Response:**
```json
{
  "message": "Retry process triggered for submissions older than 24 hours"
}
```

### POST `/api/jobs/process-all`

Process all pending submissions immediately.

**Rate Limit:** 20 requests/minute

**Query Parameters:**
- `limit` (optional): Maximum number of submissions to process

**Response:**
```json
{
  "message": "Processing 10 pending submissions in background",
  "count": 10,
  "submission_ids": [1, 2, 3, ...]
}
```

### POST `/api/jobs/process-saas/{saas_id}`

Process all pending submissions for a specific SaaS product.

**Rate Limit:** 20 requests/minute

**Response:**
```json
{
  "message": "Processing 5 submissions for SaaS: My SaaS",
  "saas_id": 1,
  "saas_name": "My SaaS",
  "count": 5,
  "submission_ids": [1, 2, 3, 4, 5]
}
```

### GET `/api/jobs/progress/{submission_id}`

Get real-time progress for a specific submission.

**Rate Limit:** 60 requests/minute

**Response:**
```json
{
  "submission_id": 1,
  "status": "filling_form",
  "progress": 50,
  "message": "Filling form fields with SaaS data",
  "started_at": "2026-01-25T00:00:00Z"
}
```

### POST `/api/jobs/batch-process`

Process multiple submissions in batch.

**Rate Limit:** 20 requests/minute

**Request Body:**
```json
{
  "submission_ids": [1, 2, 3, 4, 5]
}
```

**Response:**
```json
{
  "message": "Processing 5 submissions in background",
  "count": 5,
  "submission_ids": [1, 2, 3, 4, 5]
}
```

---

## Testing

### POST `/api/testing/save-submission`

Save test submission data (for testing purposes only).

**Rate Limit:** 100 requests/minute

**Request Body:**
```json
{
  "submission_data": {
    "fields_filled": 4,
    "total_fields": 4,
    "form_structure": {...}
  }
}
```

**Response:**
```json
{
  "message": "Test submission saved",
  "data": {...}
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message description"
}
```

### Common Status Codes

- **200 OK:** Request successful
- **201 Created:** Resource created successfully
- **400 Bad Request:** Invalid request data
- **401 Unauthorized:** Authentication required
- **403 Forbidden:** Insufficient permissions
- **404 Not Found:** Resource not found
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** Server error

### Example Error Response

```json
{
  "detail": "Submission not found"
}
```

---

## Rate Limit Headers

All responses include rate limit information in headers:

- `X-RateLimit-Limit`: Maximum requests allowed per time window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

---

## Authentication

Most endpoints require authentication via Bearer token:

```
Authorization: Bearer <access_token>
```

Currently, authentication is bypassed for development. In production, all endpoints (except `/health` and `/api/auth/login`) will require a valid token.

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- All IDs are integers
- Rate limits are per IP address
- The API uses JSON for all request/response bodies
- CORS is enabled for configured origins (see `CORS_ORIGINS` in config)
