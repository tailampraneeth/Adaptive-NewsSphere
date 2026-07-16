/**
 * Base Fetch API Wrapper for Adaptive NewsSphere API
 */
const BASE_URL = ''; // Proxied via Vite config to localhost:8000 during development

export const request = async (path, options = {}) => {
  const url = `${BASE_URL}${path}`;
  
  // Set headers
  const headers = new Headers(options.headers || {});
  
  // Set authorization if token exists
  const token = localStorage.getItem('token');
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Ensure contentType is JSON if we are passing a body
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
    options.body = JSON.stringify(options.body);
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);
    
    // Check if unauthorized
    if (response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // Dispatch custom event to let AuthContext trigger redirect
      window.dispatchEvent(new Event('auth-unauthorized'));
    }

    if (!response.ok) {
      let errorDetail = 'API Request Failed';
      try {
        const responseText = await response.text();
        try {
          const errorJson = JSON.parse(responseText);
          errorDetail = errorJson.detail || errorDetail;
        } catch (_) {
          errorDetail = responseText || errorDetail;
        }
      } catch (_) {
        // Fallback if even text() fails
      }
      throw new Error(errorDetail);
    }

    // Try parsing as JSON, return raw text or true if empty
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text();
  } catch (error) {
    console.error(`API Error on path ${path}:`, error);
    throw error;
  }
};
