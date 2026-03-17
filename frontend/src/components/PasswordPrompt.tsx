'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useAdminAuth } from '@/components/AdminAuthProvider';

export function PasswordPrompt() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { setPassword: savePassword } = useAdminAuth();
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password.trim()) {
      savePassword(password.trim());
      router.push('/admin');
    } else {
      setError('Password required');
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Admin Access</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">Enter backend password</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-secondary"
            />
            {error && <p className="text-xs text-destructive text-center">{error}</p>}
            <Button type="submit" className="w-full bg-primary cursor-pointer">
              Connect
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
