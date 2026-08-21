const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
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
  
  if (options.body instanceof FormData) {
    config.body = options.body;
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
