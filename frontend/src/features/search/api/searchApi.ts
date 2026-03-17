// Search API wrapper
export * from '@/lib/apiClient';

import { searchApi } from '@/lib/apiClient';

export async function performSearch(query: string) {
  return searchApi.search(query);
}