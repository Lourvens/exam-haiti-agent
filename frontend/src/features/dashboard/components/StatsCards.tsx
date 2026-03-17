'use client';

import { Card, CardContent } from '@/components/ui/card';
import type { DashboardStats } from '@/types/api';

interface StatsCardsProps {
  stats: DashboardStats | null;
}

const statCards = [
  { key: 'totalExams', label: 'Exams' },
  { key: 'totalChunks', label: 'Chunks' },
  { key: 'totalQuestions', label: 'Questions' },
];

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {statCards.map(({ key, label }) => {
        const value = stats ? (stats[key as keyof DashboardStats] as number) : 0;
        return (
          <Card key={key} className="bg-secondary/30 border-border/30">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground mb-1">{label}</p>
              <p className="text-2xl font-medium font-mono">{value.toLocaleString()}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
