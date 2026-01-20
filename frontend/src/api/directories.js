import { get, post, put, del } from './client';

/**
 * Directories-related API calls
 */

// Get all directories
export function getDirectories() {
  return get('/api/directories');
}

// Get a specific directory by ID
export function getDirectoryById(id) {
  return get(`/api/directories/${id}`);
}

// Create a new directory
export function createDirectory(data) {
  return post('/api/directories', data);
}

// Update an existing directory
export function updateDirectory(id, data) {
  return put(`/api/directories/${id}`, data);
}

// Delete a directory
export function deleteDirectory(id) {
  return del(`/api/directories/${id}`);
}
