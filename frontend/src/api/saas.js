import { get, post, put, del } from './client';

/**
 * SaaS-related API calls
 */

// Get all SaaS entries
export function getSaaSList() {
  return get('/api/saas');
}

// Get a specific SaaS entry by ID
export function getSaaSById(id) {
  return get(`/api/saas/${id}`);
}

// Create a new SaaS entry
export function createSaaS(data) {
  return post('/api/saas', data);
}

// Update an existing SaaS entry
export function updateSaaS(id, data) {
  return put(`/api/saas/${id}`, data);
}

// Delete a SaaS entry
export function deleteSaaS(id) {
  return del(`/api/saas/${id}`);
}
