import { get, post } from './client';

/**
 * Jobs/workflow-related API calls
 * Handles submission job management and workflow operations
 */

/**
 * Start a submission job for a SaaS product across multiple directories
 * Creates submission records and queues them for processing
 * @param {number} saasId - ID of the SaaS product to submit
 * @param {Array<number>|null} directoryIds - Optional array of directory IDs (null = all directories)
 * @returns {Promise<Object>} Job response with job_id, submissions_created, etc.
 */
export function startSubmissionJob(saasId, directoryIds = null) {
  return post('/api/jobs/start', {
    saas_id: saasId,
    directory_ids: directoryIds,
  });
}

/**
 * Get job status for a specific SaaS product
 * Returns summary of all submissions with status breakdown
 * @param {number} saasId - SaaS product ID
 * @returns {Promise<Object>} Job status with submission counts by status
 */
export function getJobStatus(saasId) {
  return get(`/api/jobs/status/${saasId}`);
}

/**
 * Manually process a specific submission
 * Triggers the complete workflow for a single submission
 * @param {number} submissionId - Submission ID to process
 * @returns {Promise<Object>} Processing status response
 */
export function processSubmission(submissionId) {
  return post(`/api/jobs/process/${submissionId}`);
}

/**
 * Get current workflow manager status
 * Returns real-time information about workflow manager state
 * @returns {Promise<Object>} Workflow status (is_running, active_tasks, config, etc.)
 */
export function getWorkflowStatus() {
  return get('/api/jobs/workflow/status');
}

/**
 * Manually trigger processing of pending submissions
 * Forces the workflow manager to process pending submissions immediately
 * @returns {Promise<Object>} Processing result with status
 */
export function triggerProcessing() {
  return post('/api/jobs/workflow/process-pending');
}

/**
 * Retry failed submissions older than specified hours
 * Resets old failed submissions to pending status for retry
 * @param {number} maxAgeHours - Maximum age in hours for failed submissions to retry (default: 24)
 * @returns {Promise<Object>} Retry operation result
 */
export function retryFailedSubmissions(maxAgeHours = 24) {
  return post(`/api/jobs/workflow/retry-failed?max_age_hours=${maxAgeHours}`, {});
}

/**
 * Get submission statistics (counts by status, success rate)
 * @param {number|null} saasId - Optional filter by SaaS product ID
 * @returns {Promise<Object>} Statistics with counts and success rate
 */
export function getSubmissionStats(saasId = null) {
  const url = saasId 
    ? `/api/submissions/stats/summary?saas_id=${saasId}`
    : '/api/submissions/stats/summary';
  return get(url);
}

/**
 * Retry a specific failed submission
 * Resets status to pending and increments retry count
 * @param {number} submissionId - Submission ID to retry
 * @returns {Promise<Object>} Updated submission with retry count
 */
export function retrySubmission(submissionId) {
  return post(`/api/submissions/${submissionId}/retry`);
}

/**
 * Process all pending submissions immediately
 * Triggers processing for all submissions with "pending" status
 * @returns {Promise<Object>} Result with count of submissions processed
 */
export function processAllPending() {
  return post('/api/jobs/process-all', {});
}
