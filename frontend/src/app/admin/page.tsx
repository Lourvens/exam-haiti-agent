'use client';

import { useEffect, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { StatsCards } from '@/features/dashboard/components/StatsCards';
import { RecentExams } from '@/features/dashboard/components/RecentExams';
import { SearchBar } from '@/features/search/components/SearchBar';
import { SearchResults } from '@/features/search/components/SearchResults';
import { UploadZone } from '@/features/ingest/components/UploadZone';
import { IngestProgress } from '@/features/ingest/components/IngestProgress';
import { PasswordPrompt } from '@/components/PasswordPrompt';
import { useAdminAuth } from '@/components/AdminAuthProvider';
import { dashboardApi, searchApi, ingestApi } from '@/lib/apiClient';
import type { DashboardStats, Exam, Chunk, IngestStatus } from '@/types/api';
import { toast } from 'sonner';

export default function AdminPage() {
  const { password } = useAdminAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentExams, setRecentExams] = useState<Exam[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Chunk[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const [isUploading, setIsUploading] = useState(false);
  const [ingestStatus, setIngestStatus] = useState<IngestStatus | null>(null);

  useEffect(() => {
    if (password) {
      loadDashboard();
    }
  }, [password]);

  const loadDashboard = async () => {
    try {
      const [statsData, examsData] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getRecentExams(),
      ]);
      setStats(statsData);
      setRecentExams(examsData);
    } catch (error: unknown) {
      console.error('Failed to load dashboard:', error);
      const err = error as { response?: { status?: number } };
      if (err.response?.status === 401) {
        toast.error('Invalid password');
      } else {
        toast.error('Error loading data');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    setIsSearching(true);
    try {
      const results = await searchApi.search(query);
      setSearchResults(results.chunks);
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const response = await ingestApi.uploadPdf(file);
      setIngestStatus({
        jobId: `job_${Date.now()}`,
        status: response.status === 'success' ? 'completed' : 'failed',
        progress: 100,
        examName: response.filename,
      });
      toast.success('File processed');
      loadDashboard();
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Upload failed - check password');
    } finally {
      setIsUploading(false);
    }
  };

  if (!password) {
    return <PasswordPrompt />;
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto max-w-4xl px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-medium">Admin Dashboard</h1>
              <p className="text-xs text-muted-foreground">Exam Haiti Agent</p>
            </div>
          </div>
          <a href="/" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
            ← Chat
          </a>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 container mx-auto max-w-4xl px-4 py-6">
        <Tabs defaultValue="dashboard" className="space-y-6">
          <TabsList className="bg-secondary/50 p-1 h-auto gap-1">
            <TabsTrigger
              value="dashboard"
              className="px-4 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-sm"
            >
              Dashboard
            </TabsTrigger>
            <TabsTrigger
              value="search"
              className="px-4 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-sm"
            >
              Search
            </TabsTrigger>
            <TabsTrigger
              value="ingest"
              className="px-4 py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground text-sm"
            >
              Ingest
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">
            {isLoading ? (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="bg-secondary/50 rounded-lg p-4">
                      <Skeleton className="h-3 w-16 mb-2" />
                      <Skeleton className="h-7 w-12" />
                    </div>
                  ))}
                </div>
                <div className="bg-secondary/50 rounded-lg p-4">
                  <Skeleton className="h-4 w-32 mb-4" />
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-12 w-full mb-2" />
                  ))}
                </div>
              </div>
            ) : (
              <>
                <StatsCards stats={stats} />
                <div className="mt-6">
                  <RecentExams exams={recentExams} />
                </div>
              </>
            )}
          </TabsContent>

          <TabsContent value="search" className="space-y-4">
            <SearchBar onSearch={handleSearch} isSearching={isSearching} />
            {isSearching ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="bg-secondary/50 rounded-lg p-4">
                    <Skeleton className="h-4 w-full mb-2" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                ))}
              </div>
            ) : searchQuery ? (
              <SearchResults results={searchResults} query={searchQuery} />
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">Enter a query to search</p>
            )}
          </TabsContent>

          <TabsContent value="ingest" className="space-y-4">
            <UploadZone onUpload={handleUpload} isUploading={isUploading} />
            {ingestStatus && (
              <div className="mt-4">
                <IngestProgress status={ingestStatus} />
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
