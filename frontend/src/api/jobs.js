import { get, post } from './client';

/**
 * Jobs/workflow-related API calls
 */

// Start a submission job
export function startSubmissionJob(saasId, directoryIds = null) {
  return post('/api/jobs/start', {
    saas_id: saasId,
    directory_ids: directoryIds,
  });
}

// Get job status for a SaaS
export function getJobStatus(saasId) {
  return get(`/api/jobs/status/${saasId}`);
}

// Process a specific submission
export function processSubmission(submissionId) {
  return post(`/api/jobs/process/${submissionId}`);
}

// Get workflow manager status
export function getWorkflowStatus() {
  return get('/api/jobs/workflow/status');
}

// Trigger processing of pending submissions
export function triggerProcessing() {
  return post('/api/jobs/workflow/process-pending');
}

// Retry failed submissions
export function retryFailedSubmissions(maxAgeHours = 24) {
  return post(`/api/jobs/workflow/retry-failed?max_age_hours=${maxAgeHours}`, {});
}

// Get submission statistics
export function getSubmissionStats(saasId = null) {
  const url = saasId 
    ? `/api/submissions/stats/summary?saas_id=${saasId}`
    : '/api/submissions/stats/summary';
  return get(url);
}

// Retry a failed submission
export function retrySubmission(submissionId) {
  return post(`/api/submissions/${submissionId}/retry`);
}
