/** TypeScript types matching backend Pydantic models */

export interface SearchRequest {
  query: string;
  dataset?: string;
  filters?: {
    weather?: string[];
    time_of_day?: string[];
    confidence_threshold?: number;
  };
  max_results?: number;
  confidence_threshold?: number;
}

export interface SearchResponse {
  job_id: string;
  status: string;
  estimated_time_seconds?: number;
  poll_url: string;
}

export interface SearchResultItem {
  frame_id?: number;
  confidence: number;
  timestamp?: string;
  thumbnail_url?: string;
  metadata: {
    gps?: [number, number] | null;
    weather?: string;
    camera_angle?: string;
    reasoning?: string;
  };
}

export interface SearchStatusResponse {
  job_id: string;
  status: string;
  progress?: {
    frames_processed: number;
    frames_total: number;
    matches_found: number;
  };
  results?: SearchResultItem[];
  error?: string;
}

export interface Collection {
  id: string;
  name: string;
  query: string;
  result_ids: number[];
  metadata?: {
    avg_confidence?: number;
    total_results?: number;
    query?: string;
  };
  created_at: string;
  creator_email?: string;
}

export interface CollectionListItem {
  id: string;
  name: string;
  query: string;
  total_results: number;
  created_at: string;
}

export interface CreateCollectionRequest {
  name: string;
  query: string;
  result_ids: number[];
  metadata?: Record<string, unknown>;
}

