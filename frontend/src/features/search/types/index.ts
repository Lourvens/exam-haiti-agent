// Search feature types
export * from '@/types/api';

export interface SearchState {
  query: string;
  results: import('@/types/api').Chunk[];
  isSearching: boolean;
  error: string | null;
}