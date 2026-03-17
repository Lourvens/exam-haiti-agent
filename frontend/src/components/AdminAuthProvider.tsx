'use client';

import { useState, createContext, useContext, useEffect, type ReactNode } from 'react';

interface AuthContextType {
  password: string | null;
  setPassword: (pwd: string) => void;
  clearPassword: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const STORAGE_KEY = 'exam_agent_admin_pwd';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [password, setPasswordState] = useState<string | null>(null);

  useEffect(() => {
    // Load password from localStorage on mount
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) setPasswordState(stored);
  }, []);

  const setPassword = (pwd: string) => {
    localStorage.setItem(STORAGE_KEY, pwd);
    setPasswordState(pwd);
  };

  const clearPassword = () => {
    localStorage.removeItem(STORAGE_KEY);
    setPasswordState(null);
  };

  return (
    <AuthContext.Provider value={{ password, setPassword, clearPassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAdminAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAdminAuth must be used within AuthProvider');
  }
  return context;
}
