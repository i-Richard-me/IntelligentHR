'use client';

import { DashboardLayout } from '@/components/shared/layout/DashboardLayout';
import { Toaster } from '@/components/ui/toaster';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardLayout>
      {children}
      <Toaster />
    </DashboardLayout>
  );
}