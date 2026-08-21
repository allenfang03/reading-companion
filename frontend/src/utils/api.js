const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const USER_ID_KEY = 'reading_companion_user_id';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

// Generate a UUID v4
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// Get or create user ID
export function getUserId() {
  let userId = localStorage.getItem(USER_ID_KEY);
  if (!userId) {
    userId = generateUUID();
    localStorage.setItem(USER_ID_KEY, userId);
  }
  return userId;
}

// Get user ID from localStorage
export function getStoredUserId() {
  return localStorage.getItem(USER_ID_KEY);
}

async function request(endpoint, options = {}) {
  // Always include user_id in requests
  const userId = getUserId();
  const separator = endpoint.includes('?') ? '&' : '?';
  const url = `${API_BASE}${endpoint}${separator}user_id=${encodeURIComponent(userId)}`;
  
  const config = {
    headers: {
      ...options.headers,
    },
    ...options,
  };
  
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
    config.body = JSON.stringify(options.body);
  }
  
  // For FormData, body is passed as-is (user_id is in URL query param)
  if (options.body instanceof FormData) {
    // Do not set Content-Type for FormData - browser sets it with boundary
    delete config.headers['Content-Type'];
  }
  
  try {
    const response = await fetch(url, config);
    const data = await response.json();
    
    if (!response.ok) {
      throw new ApiError(
        data.message || 'An error occurred',
        response.status,
        data
      );
    }
    
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message || 'Network error', 0, null);
  }
}

export const api = {
  // Books
  async listBooks() {
    return request('/books');
  },
  
  async uploadBook(file, onProgress) {
    const formData = new FormData();
    formData.append('file', file);
    
    return request('/books/upload', {
      method: 'POST',
      body: formData,
    });
  },
  
  // Sessions
  async getSession(sessionToken) {
    return request(`/sessions/${sessionToken}`);
  },
  
  async setPosition(bookId, snippet) {
    return request('/sessions/set-position', {
      method: 'POST',
      body: { book_id: bookId, snippet },
    });
  },
  
  // Recap
  async getRecap(sessionToken) {
    return request(`/recap?session_token=${encodeURIComponent(sessionToken)}`);
  },
  
  // Character
  async lookupCharacter(sessionToken, name) {
    return request(`/character?session_token=${encodeURIComponent(sessionToken)}&name=${encodeURIComponent(name)}`);
  },
};

export { ApiError };
