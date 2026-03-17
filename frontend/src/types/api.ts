// Shared API types for the frontend

// ============================================================================
// Public API Types
// ============================================================================

export interface ApiStatus {
  name: string;
  version: string;
  status: string;
}

export interface HealthCheck {
  status: 'healthy';
}

// ============================================================================
// Admin API Types - Ingest
// ============================================================================

export interface IngestResponse {
  status: 'success' | 'error';
  filename: string;
  chunks: number;
  total_in_collection: number;
  message: string;
}

export interface IngestStatus {
  jobId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  examName?: string;
  error?: string;
}

// ============================================================================
// Admin API Types - Chunks
// ============================================================================

export interface Chunk {
  id: string;
  content: string;
  metadata: ChunkMetadata;
}

export interface ChunkMetadata {
  source?: string;
  exam_id?: string;
  exam_name?: string;
  subject?: string;
  year?: string | number;
  serie?: string;
  section?: string;
  page?: number;
  question_number?: number;
  [key: string]: unknown;
}

export interface ChunksResponse {
  chunks: Chunk[];
  total: number;
  limit: number;
  offset: number;
}

// ============================================================================
// Admin API Types - Exams
// ============================================================================

// API response format (raw data from backend)
export interface ExamResponse {
  exam_id: string;
  source: string;
  subject: string;
  year: string | number;
  serie: string;
  chunk_count: number;
}

export interface ExamsResponse {
  exams: ExamResponse[];
  total: number;
}

// Dashboard format (transformed for UI)
export interface Exam {
  id: string;
  name: string;
  year: number;
  session: string;
  subject: string;
  createdAt: string;
  chunkCount: number;
  status: 'completed' | 'processing' | 'failed';
}

// ============================================================================
// Admin API Types - Graph
// ============================================================================

export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, unknown>;
}

export interface GraphNodesResponse {
  nodes: GraphNode[];
  count: number;
  type_filter: string | null;
}

export interface GraphStatsResponse {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

export interface GraphSyncResponse {
  status: 'success' | 'error';
  mode: 'standard' | 'llm_enhanced';
  result: {
    exams_created?: number;
    sections_created?: number;
    questions_created?: number;
    relationships_created?: number;
    message?: string;
  };
}

// ============================================================================
// Dashboard & Search Types (for frontend features)
// ============================================================================

export interface DashboardStats {
  totalExams: number;
  totalChunks: number;
  totalQuestions: number;
  recentActivity: {
    date: string;
    count: number;
  }[];
}

export interface SearchResult {
  chunks: Chunk[];
  total: number;
  query: string;
}

// ============================================================================
// Agent API Types
// ============================================================================

export interface AgentQueryRequest {
  query: string;
  filters?: {
    subject?: string;
    year?: number;
    serie?: string;
    topic?: string;
  };
}

export interface AgentQueryResponse {
  answer: string;
  sources: AgentSource[];
  search_type: 'graph' | 'embed' | 'hybrid';
  filters: Record<string, unknown>;
}

export interface AgentSource {
  type: 'graph' | 'embed';
  id?: string;
  content?: string;
  metadata?: Record<string, unknown>;
}

export interface AgentHealth {
  status: string;
  llm_configured: boolean;
  neo4j_enabled: boolean;
  chroma_available: boolean;
  neo4j_available?: boolean;
}

// ============================================================================
// API Error Types
// ============================================================================

export interface ApiError {
  detail: string;
}

export interface ApiErrorResponse {
  status: number;
  message: string;
  data?: unknown;
}
