'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ModelConfigTab } from '@/components/features/feature-config/ModelConfigTab';

export default function FeatureConfigPage() {
  const [activeTab, setActiveTab] = useState('model-config');

  return (
    <div className="flex-1 space-y-8 p-4 md:p-8 pt-6">
      {/* 标题区域 */}
      <div className="border-b pb-6">
        <div className="container px-0">
          <div className="flex flex-col gap-4">
            <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground/90">功能配置</h1>
            <p className="text-sm md:text-base text-muted-foreground max-w-3xl">
              在这里可以管理系统的各项功能配置，包括业务分析模型、系统参数等设置。
            </p>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <Card>
        <CardHeader>
          <CardTitle>配置管理</CardTitle>
          <CardDescription>
            选择需要管理的配置类型，进行查看和修改。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs
            defaultValue="model-config"
            value={activeTab}
            onValueChange={setActiveTab}
            className="space-y-4"
          >
            <TabsList>
              <TabsTrigger value="model-config">业务分析模型</TabsTrigger>
              <TabsTrigger value="system-params" disabled>系统参数</TabsTrigger>
              <TabsTrigger value="api-config" disabled>API 配置</TabsTrigger>
            </TabsList>

            <TabsContent value="model-config" className="space-y-4">
              <Alert>
                <AlertDescription>
                  在这里可以配置系统支持的各种业务分析模型，包括模型名称、分析规则、验证指令等。
                </AlertDescription>
              </Alert>
              <ModelConfigTab />
            </TabsContent>

            <TabsContent value="system-params">
              <Alert>
                <AlertDescription>
                  系统参数配置功能正在开发中...
                </AlertDescription>
              </Alert>
            </TabsContent>

            <TabsContent value="api-config">
              <Alert>
                <AlertDescription>
                  API 配置功能正在开发中...
                </AlertDescription>
              </Alert>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}