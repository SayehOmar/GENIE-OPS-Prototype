import { get, post, put, del } from './client';

/**
 * Submissions-related API calls
 */

// Get all submissions (with optional filters)
export function getSubmissions(saasId = null, directoryId = null) {
  let url = '/api/submissions';
  const params = [];
  if (saasId) params.push(`saas_id=${saasId}`);
  if (directoryId) params.push(`directory_id=${directoryId}`);
  if (params.length > 0) url += '?' + params.join('&');
  return get(url);
}

// Get a specific submission by ID
export function getSubmissionById(id) {
  return get(`/api/submissions/${id}`);
}

// Create a new submission
export function createSubmission(data) {
  return post('/api/submissions', data);
}

// Update an existing submission
export function updateSubmission(id, data) {
  return put(`/api/submissions/${id}`, data);
}

// Delete a submission
export function deleteSubmission(id) {
  return del(`/api/submissions/${id}`);
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
