// Dashboard API wrapper
export * from '@/lib/apiClient';

import { dashboardApi } from '@/lib/apiClient';

export async function fetchDashboardData() {
  const [stats, recentExams] = await Promise.all([
    dashboardApi.getStats(),
    dashboardApi.getRecentExams(),
  ]);

  return { stats, recentExams };
}