import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { AppSidebar } from '@/components/shared/layout/AppSidebar';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

interface DashboardLayoutProps {
  children: ReactNode;
}

// 页面路径配置
const pathConfig = {
  '/text-review': {
    parent: { label: '文本分析', path: '' },
    current: '文本评估'
  },
  '/text-classification': {
    parent: { label: '文本分析', path: '' },
    current: '文本分类'
  },
  '/data-cleaning': {
    parent: { label: '数据处理', path: '' },
    current: '数据清洗'
  },
  '/python-analysis': {
    parent: { label: '数据分析', path: '' },
    current: '数据分析'
  },
  '/feature-config': {
    parent: { label: '系统设置', path: '' },
    current: '功能配置'
  }
};

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const currentPath = pathConfig[pathname as keyof typeof pathConfig];

  return (
    <SidebarProvider className="flex h-screen w-full overflow-hidden">
      <AppSidebar />
      <SidebarInset className="flex flex-col min-w-0 flex-1">
        <header className="sticky top-0 flex h-14 shrink-0 items-center gap-2 bg-background border-b">
          <div className="flex flex-1 items-center gap-2 px-3">
            <SidebarTrigger />
            <Separator orientation="vertical" className="mr-2 h-4" />
            {currentPath && (
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem className="hidden md:block">
                    <BreadcrumbLink href={currentPath.parent.path} asChild>
                      <Link href={currentPath.parent.path}>
                        {currentPath.parent.label}
                      </Link>
                    </BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator className="hidden md:block" />
                  <BreadcrumbItem>
                    <BreadcrumbPage>{currentPath.current}</BreadcrumbPage>
                  </BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}