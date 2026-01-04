/** API client for EdgeVLM backend */

import type {
  SearchRequest,
  SearchResponse,
  SearchStatusResponse,
  Collection,
  CollectionListItem,
  CreateCollectionRequest,
} from '../types';

// Use proxy in dev mode (Vite proxies /api to localhost:8000)
// In production, use VITE_API_URL environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '/api' : 'http://localhost:8000');

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Search endpoints
  createSearch: async (request: SearchRequest): Promise<SearchResponse> => {
    return fetchAPI<SearchResponse>('/search', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  getSearchStatus: async (jobId: string): Promise<SearchStatusResponse> => {
    return fetchAPI<SearchStatusResponse>(`/search/${jobId}`);
  },

  // Collection endpoints
  createCollection: async (request: CreateCollectionRequest): Promise<Collection> => {
    return fetchAPI<Collection>('/collections', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  listCollections: async (): Promise<CollectionListItem[]> => {
    return fetchAPI<CollectionListItem[]>('/collections');
  },

  getCollection: async (id: string): Promise<Collection> => {
    return fetchAPI<Collection>(`/collections/${id}`);
  },

  exportCollection: async (id: string, format: 'csv' | 'json'): Promise<Blob> => {
    const response = await fetch(`${API_BASE_URL}/export/${id}?format=${format}`);
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    return response.blob();
  },

  // Thumbnail endpoint
  getThumbnail: (frameId: number): string => {
    return `${API_BASE_URL}/thumbnails/${frameId}`;
  },

  // Stats endpoint
  getStats: async (): Promise<{ total_frames: number; total_collections: number; has_data: boolean }> => {
    return fetchAPI<{ total_frames: number; total_collections: number; has_data: boolean }>('/stats');
  },
};

