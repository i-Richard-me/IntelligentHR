'use client';

import { DashboardLayout } from '@/components/shared/layout/DashboardLayout';
import { Toaster } from '@/components/ui/toaster';
import { useEffect } from 'react';

const TEMP_USER_ID = 'user_123';

export default function Layout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // 如果 localStorage 中没有 userId，则设置一个临时的
    if (!localStorage.getItem('userId')) {
      localStorage.setItem('userId', TEMP_USER_ID);
    }
  }, []);

  return (
    <DashboardLayout>
      {children}
      <Toaster />
    </DashboardLayout>
  );
}