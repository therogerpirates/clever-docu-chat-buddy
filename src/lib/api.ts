const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Ensure headers are set
  const headers = new Headers(options.headers);
  
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
  
  const response = await fetch(url, fetchOptions);
  
  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch (e) {
      errorData = { message: await response.text() };
    }
    
    const error = new Error(errorData.message || 'API request failed');
    (error as any).status = response.status;
    (error as any).data = errorData;
    throw error;
  }
  
  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    return null;
  }
  
  return response.json();
};

export const uploadFile = async (formData: FormData) => {
  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
    headers: {
      'Accept': 'application/json'
    }
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

export const fetchFiles = async () => {
  const response = await fetch(`${API_BASE_URL}/api/files/`, {
    method: 'GET',
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to fetch files');
  }

  return response.json();
};

export const deleteFile = async (fileId: string | number) => {
  const response = await fetch(`${API_BASE_URL}/api/files/${fileId}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to delete file');
  }

  return response.json();
};
