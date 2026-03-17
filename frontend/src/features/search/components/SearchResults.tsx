'use client';

import { Card, CardContent } from '@/components/ui/card';

interface ChunkWithScore {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
  score?: number;
}

interface SearchResultsProps {
  results: ChunkWithScore[];
  query: string;
}

export function SearchResults({ results, query }: SearchResultsProps) {
  if (results.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">No results for &quot;{query}&quot;</p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{results.length} results</p>
      {results.map((result) => (
        <Card key={result.id} className="bg-secondary/30 border-border/30 hover:border-primary/30 transition-colors">
          <CardContent className="p-4">
            <p className="text-sm">{result.content}</p>
            <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
              <span>{(result.metadata.exam_name as string) || (result.metadata.subject as string) || 'Unknown'}</span>
              {result.score && <span className="font-mono">{Math.round(result.score * 100)}%</span>}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
