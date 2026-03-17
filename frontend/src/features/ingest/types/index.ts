// Ingest feature types
export * from '@/types/api';

export interface IngestState {
  file: File | null;
  isUploading: boolean;
  progress: number;
  status: import('@/types/api').IngestStatus | null;
  error: string | null;
}