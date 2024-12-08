// src/app/(dashboard)/feature-config/page.tsx

'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SidebarInset } from "@/components/ui/sidebar";
import { ConfigSidebar, featureModules, type FeatureModuleId } from '@/components/features/feature-config/ConfigSidebar';
import { DataCleaningConfig } from '@/components/features/feature-config/DataCleaningConfig';

export default function FeatureConfigPage() {
  const [activeModule, setActiveModule] = useState<FeatureModuleId>('data_cleaning');

  // 渲染当前选中模块的配置界面
  const renderModuleConfig = () => {
    switch (activeModule) {
      case 'data_cleaning':
        return <DataCleaningConfig />;
      case 'text_review':
      case 'text_classification':
      case 'semantic_analysis':
        return (
          <div className="flex items-center justify-center h-[60vh] text-muted-foreground">
            {featureModules[activeModule].title}功能的配置界面正在开发中...
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-1 overflow-hidden">
      <SidebarInset className="flex flex-col min-w-0 flex-1">
        <div className="flex-1 space-y-8 p-4 md:p-8 pt-6 overflow-auto">
          {/* 标题区域 */}
          <div className="border-b pb-6">
            <div className="container px-0">
              <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
                {/* 标题和描述 */}
                <div className="space-y-3">
                  <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground/90">
                    {featureModules[activeModule].title}
                  </h1>
                  <p className="text-sm md:text-base text-muted-foreground max-w-3xl">
                    {featureModules[activeModule].description}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 主要内容区域 */}
          <Card>
            <CardHeader>
              <CardTitle>配置管理</CardTitle>
              <CardDescription>
                配置{featureModules[activeModule].title}功能的相关参数和规则。
              </CardDescription>
            </CardHeader>
            <CardContent>
              {renderModuleConfig()}
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
      <ConfigSidebar
        side="right"
        activeModule={activeModule}
        onModuleChange={setActiveModule}
      />
    </div>
  );
}