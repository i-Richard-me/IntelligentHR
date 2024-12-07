'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ModelConfigTab } from '@/components/features/feature-config/ModelConfigTab';
import { CollectionConfigTab } from '@/components/features/feature-config/CollectionConfigTab';

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
              在这里可以管理系统的各项功能配置，包括业务分析模型、向量数据库、系统参数等设置。
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
            <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
              <TabsTrigger value="model-config">业务分析模型</TabsTrigger>
              <TabsTrigger value="collection-config">向量数据库</TabsTrigger>
            </TabsList>

            <TabsContent value="model-config" className="space-y-4">
              <Alert>
                <AlertDescription>
                  在这里可以配置系统支持的各种业务分析模型，包括模型名称、分析规则、验证指令等。
                </AlertDescription>
              </Alert>
              <ModelConfigTab />
            </TabsContent>

            <TabsContent value="collection-config" className="space-y-4">
              <Alert>
                <AlertDescription>
                  在这里可以管理向量数据库中的 Collection 配置，包括字段定义、向量化设置等。
                </AlertDescription>
              </Alert>
              <CollectionConfigTab />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}