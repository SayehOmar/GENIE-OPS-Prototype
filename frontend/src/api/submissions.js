import { get, post, put, del } from './client';

/**
 * Submissions-related API calls
 */

// Get all submissions
export function getSubmissions() {
    return get('/api/submissions');
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
