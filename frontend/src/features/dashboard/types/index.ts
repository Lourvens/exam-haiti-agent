// Dashboard feature types
export * from '@/types/api';

export interface DashboardState {
  stats: import('@/types/api').DashboardStats | null;
  recentExams: import('@/types/api').Exam[];
  isLoading: boolean;
  error: string | null;
}