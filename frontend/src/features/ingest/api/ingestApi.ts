// Ingest API wrapper
export * from '@/lib/apiClient';

import { ingestApi } from '@/lib/apiClient';
import type { IngestResponse, IngestStatus } from '@/types/api';

export async function uploadExam(file: File): Promise<IngestStatus> {
  const response = await ingestApi.uploadPdf(file);

  // Transform IngestResponse to IngestStatus for UI compatibility
  return {
    jobId: `job_${Date.now()}`,
    status: response.status === 'success' ? 'completed' : 'failed',
    progress: response.status === 'success' ? 100 : 0,
    examName: response.filename,
    error: response.status === 'error' ? response.message : undefined,
  };
}
