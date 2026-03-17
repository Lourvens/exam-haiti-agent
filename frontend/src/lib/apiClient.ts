import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import type {
  ApiStatus,
  HealthCheck,
  IngestResponse,
  ChunksResponse,
  ExamsResponse,
  ExamResponse,
  Exam,
  GraphNodesResponse,
  GraphStatsResponse,
  GraphSyncResponse,
  Chunk,
  GraphNode,
  DashboardStats,
  AgentQueryRequest,
  AgentQueryResponse,
  AgentHealth,
} from '@/types/api';

// ============================================================================
// Configuration
// ============================================================================

const getApiUrl = (): string => {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
};

const getAdminPassword = (): string | undefined => {
  if (typeof window === 'undefined') return undefined;
  return localStorage.getItem('exam_agent_admin_pwd') || undefined;
};

// ============================================================================
// API Client Setup
// ============================================================================

const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: getApiUrl(),
    timeout: 60000, // 60 seconds for file uploads
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor to add auth token
  client.interceptors.request.use(
    (config) => {
      const token = getAdminPassword();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      if (error.response) {
        // Server responded with error status
        const status = error.response.status;
        const data = error.response.data as { detail?: string } | undefined;

        if (status === 401) {
          console.error('Authentication failed: Invalid or missing admin password');
        } else if (status === 403) {
          console.error('Forbidden: Insufficient permissions');
        } else if (status === 500) {
          console.error('Server error:', data?.detail || 'Unknown error');
        }
      } else if (error.request) {
        // Request made but no response received
        console.error('Network error: No response from server');
      } else {
        console.error('Request error:', error.message);
      }
      return Promise.reject(error);
    }
  );

  return client;
};

const apiClient = createApiClient();

// ============================================================================
// Helper Functions
// ============================================================================

const transformExamToListItem = (exam: ExamResponse): Exam => {
  // Transform API exam to dashboard-compatible format
  const year = typeof exam.year === 'string' ? parseInt(exam.year, 10) : exam.year;
  const name = exam.subject
    ? `Baccalauréat Série ${exam.serie || '?'} - ${exam.subject} ${year}`
    : exam.exam_id;

  return {
    id: exam.exam_id,
    name,
    year,
    session: 'Juillet', // Default session since not stored
    subject: exam.subject || 'Unknown',
    createdAt: new Date().toISOString(), // Not provided by API
    chunkCount: exam.chunk_count,
    status: 'completed',
  };
};

const calculateDashboardStats = (exams: ExamResponse[], chunksTotal: number): DashboardStats => {
  return {
    totalExams: exams.length,
    totalChunks: chunksTotal,
    totalQuestions: 0, // Not directly available
    recentActivity: [
      { date: new Date().toISOString().split('T')[0], count: exams.length },
    ],
  };
};

// ============================================================================
// Public API
// ============================================================================

export const publicApi = {
  /**
   * Get API status
   * GET /
   */
  getStatus: async (): Promise<ApiStatus> => {
    const response = await apiClient.get<ApiStatus>('/');
    return response.data;
  },

  /**
   * Health check
   * GET /health
   */
  checkHealth: async (): Promise<HealthCheck> => {
    const response = await apiClient.get<HealthCheck>('/health');
    return response.data;
  },
};

// ============================================================================
// Admin API - Ingest
// ============================================================================

export const ingestApi = {
  /**
   * Upload and ingest a PDF file
   * POST /admin/ingest
   */
  uploadPdf: async (file: File): Promise<IngestResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<IngestResponse>('/admin/ingest', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },
};

// ============================================================================
// Admin API - Chunks
// ============================================================================

export const chunksApi = {
  /**
   * Get chunks from Chroma
   * GET /admin/chunks
   */
  getChunks: async (params?: {
    examId?: string;
    limit?: number;
    offset?: number;
  }): Promise<ChunksResponse> => {
    const config: AxiosRequestConfig = {
      params: {
        limit: params?.limit || 50,
        offset: params?.offset || 0,
      },
    };

    if (params?.examId) {
      config.params.exam_id = params.examId;
    }

    const response = await apiClient.get<ChunksResponse>('/admin/chunks', config);
    return response.data;
  },
};

// ============================================================================
// Admin API - Exams
// ============================================================================

export const examsApi = {
  /**
   * List all exams
   * GET /admin/exams
   */
  listExams: async (): Promise<ExamsResponse> => {
    const response = await apiClient.get<ExamsResponse>('/admin/exams');
    return response.data;
  },
};

// ============================================================================
// Admin API - Graph
// ============================================================================

export const graphApi = {
  /**
   * Get graph nodes from Neo4j
   * GET /admin/graph/nodes
   */
  getNodes: async (params?: {
    type?: string;
    limit?: number;
  }): Promise<GraphNodesResponse> => {
    const config: AxiosRequestConfig = {
      params: {
        limit: params?.limit || 100,
      },
    };

    if (params?.type) {
      config.params.type = params.type;
    }

    const response = await apiClient.get<GraphNodesResponse>('/admin/graph/nodes', config);
    return response.data;
  },

  /**
   * Get graph statistics
   * GET /admin/graph/stats
   */
  getStats: async (): Promise<GraphStatsResponse> => {
    const response = await apiClient.get<GraphStatsResponse>('/admin/graph/stats');
    return response.data;
  },

  /**
   * Sync from Chroma to Neo4j
   * POST /admin/graph/sync
   */
  sync: async (llm = false): Promise<GraphSyncResponse> => {
    const response = await apiClient.post<GraphSyncResponse>('/admin/graph/sync', null, {
      params: { llm },
    });
    return response.data;
  },
};

// ============================================================================
// Dashboard API (combines multiple endpoints for dashboard)
// ============================================================================

export const dashboardApi = {
  /**
   * Get dashboard statistics
   */
  getStats: async (): Promise<DashboardStats> => {
    try {
      const [examsResponse, chunksResponse] = await Promise.all([
        examsApi.listExams(),
        chunksApi.getChunks({ limit: 1 }), // Just to get total count
      ]);

      return calculateDashboardStats(examsResponse.exams, chunksResponse.total);
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error);
      throw error;
    }
  },

  /**
   * Get recent exams
   */
  getRecentExams: async (limit = 5): Promise<Exam[]> => {
    try {
      const response = await examsApi.listExams();
      // Transform and sort by chunk count (descending), take first `limit`
      const sortedExams = response.exams
        .sort((a, b) => b.chunk_count - a.chunk_count)
        .slice(0, limit);

      return sortedExams.map(transformExamToListItem);
    } catch (error) {
      console.error('Failed to fetch recent exams:', error);
      throw error;
    }
  },
};

// ============================================================================
// Search API (for future implementation)
// ============================================================================

export const searchApi = {
  /**
   * Search chunks (placeholder - implementation depends on search endpoint)
   */
  search: async (_query: string): Promise<{ chunks: Chunk[]; total: number; query: string }> => {
    // Search endpoint not implemented in backend yet
    // This would be: POST /search with { query }
    console.warn('Search endpoint not implemented in backend');
    return {
      chunks: [],
      total: 0,
      query: _query,
    };
  },
};

// ============================================================================
// Agent API
// ============================================================================

export const agentApi = {
  /**
   * Query the exam agent with natural language
   * POST /agent/query
   */
  query: async (request: AgentQueryRequest): Promise<AgentQueryResponse> => {
    const response = await apiClient.post<AgentQueryResponse>('/agent/query', request);
    return response.data;
  },

  /**
   * Get agent health status
   * GET /agent/health
   */
  getHealth: async (): Promise<AgentHealth> => {
    const response = await apiClient.get<AgentHealth>('/agent/health');
    return response.data;
  },
};

// ============================================================================
// Export
// ============================================================================

export default apiClient;
