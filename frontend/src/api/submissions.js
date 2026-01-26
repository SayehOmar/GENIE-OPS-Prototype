import { get, post, put, del } from './client';

/**
 * Submissions-related API calls
 * Handles all HTTP requests for submission management
 */

/**
 * Get all submissions with optional filtering
 * @param {number|null} saasId - Optional filter by SaaS product ID
 * @param {number|null} directoryId - Optional filter by directory ID
 * @returns {Promise<Array>} Array of submission objects
 */
export function getSubmissions(saasId = null, directoryId = null) {
  let url = '/api/submissions';
  const params = [];
  if (saasId) params.push(`saas_id=${saasId}`);
  if (directoryId) params.push(`directory_id=${directoryId}`);
  if (params.length > 0) url += '?' + params.join('&');
  return get(url);
}

/**
 * Get a specific submission by its ID
 * @param {number} id - Submission ID
 * @returns {Promise<Object>} Submission object with all details
 */
export function getSubmissionById(id) {
  return get(`/api/submissions/${id}`);
}

/**
 * Create a new submission record
 * @param {Object} data - Submission data (saas_id, directory_id, status, form_data)
 * @returns {Promise<Object>} Created submission object
 */
export function createSubmission(data) {
  return post('/api/submissions', data);
}

/**
 * Update an existing submission
 * @param {number} id - Submission ID to update
 * @param {Object} data - Fields to update (status, error_message, form_data, etc.)
 * @returns {Promise<Object>} Updated submission object
 */
export function updateSubmission(id, data) {
  return put(`/api/submissions/${id}`, data);
}

/**
 * Delete a submission permanently
 * @param {number} id - Submission ID to delete
 * @returns {Promise<Object>} Success message
 */
export function deleteSubmission(id) {
  return del(`/api/submissions/${id}`);
}

/**
 * Get submission statistics (counts by status, success rate)
 * @param {number|null} saasId - Optional filter by SaaS product ID
 * @returns {Promise<Object>} Statistics object with counts and success rate
 */
export function getSubmissionStats(saasId = null) {
  const url = saasId 
    ? `/api/submissions/stats/summary?saas_id=${saasId}`
    : '/api/submissions/stats/summary';
  return get(url);
}

/**
 * Retry a failed or pending submission
 * Resets status to pending and increments retry count
 * @param {number} submissionId - Submission ID to retry
 * @returns {Promise<Object>} Response with updated submission and retry count
 */
export function retrySubmission(submissionId) {
  return post(`/api/submissions/${submissionId}/retry`);
}

/**
 * Stop automatic retry for a failed submission
 * Sets status to auto_retry_failed_{x} where x increments from 1 to 5
 * @param {number} submissionId - Submission ID to stop auto-retry for
 * @returns {Promise<Object>} Response with updated submission and stop count
 */
export function stopAutoRetry(submissionId) {
  return post(`/api/submissions/${submissionId}/stop-retry`);
}
