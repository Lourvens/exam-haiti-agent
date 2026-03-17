'use client';

import { Card, CardContent } from '@/components/ui/card';
import type { IngestStatus } from '@/types/api';

interface IngestProgressProps {
  status: IngestStatus | null;
}

export function IngestProgress({ status }: IngestProgressProps) {
  if (!status) return null;

  const statusColor = {
    completed: 'bg-green-500',
    processing: 'bg-blue-500',
    failed: 'bg-red-500',
    pending: 'bg-muted-foreground',
  }[status.status] || 'bg-muted-foreground';

  return (
    <Card className="bg-secondary/30 border-border/30">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${statusColor}`} />
          <span className="text-sm capitalize">{status.status}</span>
          {status.progress > 0 && <span className="text-xs text-muted-foreground">{status.progress}%</span>}
        </div>
        {status.error && <p className="text-xs text-destructive mt-2">{status.error}</p>}
      </CardContent>
    </Card>
  );
}
