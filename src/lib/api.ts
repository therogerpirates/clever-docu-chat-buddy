const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Ensure headers are set
  const headers = new Headers(options.headers);
  
  // Add authentication token if available
  const token = localStorage.getItem('access_token');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  // Only set Content-Type if it's not a FormData object and not already set
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  
  // Add credentials for CORS
  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: 'include',
  };
  
  console.log('Making request to:', url, 'with headers:', Object.fromEntries(headers.entries()));
  const response = await fetch(url, fetchOptions);
  
  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch (e) {
      errorData = { message: await response.text() };
    }
    
    // If unauthorized, clear token and redirect to login
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      return;
    }
    
    // Extract error message from different possible response formats
    let errorMessage = 'API request failed';
    if (errorData.error) {
      errorMessage = errorData.error;
      if (errorData.details) {
        errorMessage += `: ${errorData.details}`;
      }
    } else if (errorData.message) {
      errorMessage = errorData.message;
    } else if (errorData.detail) {
      errorMessage = errorData.detail;
    } else if (typeof errorData === 'string') {
      errorMessage = errorData;
    }
    
    const error = new Error(errorMessage);
    (error as any).status = response.status;
    (error as any).data = errorData;
    console.error('API Error:', { status: response.status, error: errorData });
    throw error;
  }
  
  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    return null;
  }
  
  return response.json();
};

// Helper function to get auth headers
const getAuthHeaders = (): Headers => {
  const headers = new Headers();
  const token = localStorage.getItem('access_token');
  if (token) {
    headers.append('Authorization', `Bearer ${token}`);
  }
  return headers;
};

export async function uploadFile(formData: FormData) {
  const token = localStorage.getItem('access_token');
  const response = await fetch('http://localhost:8000/api/upload/file', {
    method: 'POST',
    body: formData,
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export const uploadWebsite = async (url: string, description: string = 'Website upload') => {
  try {
    const headers = getAuthHeaders();
    headers.append('Content-Type', 'application/json');
    
    const response = await fetch(`${API_BASE_URL}/api/upload/website`, {
      method: 'POST',
      headers,
      credentials: 'include' as RequestCredentials,
      body: JSON.stringify({
        url,
        description
      })
    });
    
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        errorData = { message: await response.text() };
      }
      
      // Handle 401 Unauthorized
      if (response.status === 401) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        throw new Error('Unauthorized - Please log in again');
      }
      
      const error = new Error(errorData.detail || errorData.message || 'Website upload failed');
      (error as any).status = response.status;
      (error as any).data = errorData;
      throw error;
    }
    
    return response.json();
  } catch (error) {
    console.error('Website upload error:', error);
    throw error;
  }
};

export const fetchFiles = async () => {
  return apiRequest('/api/upload/');
};

export const deleteFile = async (fileId: string | number) => {
  return apiRequest(`/api/files/${fileId}`, {
    method: 'DELETE',
  });
};

// New functions for file restrictions
export const setFileRestrictions = async (fileId: string | number, userIds: number[]) => {
  return apiRequest(`/api/files/${fileId}/restrictions`, {
    method: 'POST',
    body: JSON.stringify({ user_ids: userIds })
  });
};

export const getFileRestrictions = async (fileId: string | number) => {
  return apiRequest(`/api/files/${fileId}/restrictions`);
};

export const fetchUsers = async () => {
  return apiRequest('/api/users');
};

// Auth
export const login = async (credentials: { username: string, password: string }) => {
  return apiRequest('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
};

export const getCurrentUser = async () => {
  return apiRequest('/api/auth/me');
};

// Files
export const getFileDetails = async (fileId: string | number) => {
  return apiRequest(`/api/files/${fileId}`);
};

export const reprocessFile = async (fileId: string | number) => {
  return apiRequest(`/api/files/${fileId}/reprocess`, {
    method: 'POST',
  });
};
