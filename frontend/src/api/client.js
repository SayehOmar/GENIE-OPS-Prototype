// API client configuration and base utilities
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Base fetch wrapper with error handling
 */
async function apiRequest(endpoint, options = {}) {
  // Remove trailing slash to avoid redirect issues
  const cleanEndpoint = endpoint.replace(/\/$/, '');
  const url = `${API_BASE_URL}${cleanEndpoint}`;
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
    redirect: 'follow', // Follow redirects but handle CORS properly
  };

  try {
    const response = await fetch(url, config);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

/**
 * GET request
 */
export function get(endpoint, options = {}) {
  return apiRequest(endpoint, {
    method: 'GET',
    ...options,
  });
}

/**
 * POST request
 */
export function post(endpoint, data, options = {}) {
  return apiRequest(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
    ...options,
  });
}

/**
 * PUT request
 */
export function put(endpoint, data, options = {}) {
  return apiRequest(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
    ...options,
  });
}

/**
 * DELETE request
 */
export function del(endpoint, options = {}) {
  return apiRequest(endpoint, {
    method: 'DELETE',
    ...options,
  });
}

export default {
  get,
  post,
  put,
  delete: del,
};
