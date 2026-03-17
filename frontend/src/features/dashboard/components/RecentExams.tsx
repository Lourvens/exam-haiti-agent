'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Exam } from '@/types/api';

interface RecentExamsProps {
  exams: Exam[];
}

export function RecentExams({ exams }: RecentExamsProps) {
  return (
    <Card className="bg-secondary/30 border-border/30">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Recent Exams</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          {exams.map((exam) => (
            <div
              key={exam.id}
              className="flex items-center justify-between py-2 px-2 -mx-2 rounded-md hover:bg-secondary/30 transition-colors"
            >
              <p className="text-sm truncate">{exam.name}</p>
              <span className="text-xs text-muted-foreground ml-2 font-mono">{exam.chunkCount}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
