'use client';

import { useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ModelConfigTab } from './ModelConfigTab';
import { CollectionConfigTab } from './CollectionConfigTab';
import { CollectionDataTab } from './CollectionDataTab';

export function DataCleaningConfig() {
  const [activeTab, setActiveTab] = useState('model-config');

  return (
    <Tabs
      defaultValue="model-config"
      value={activeTab}
      onValueChange={setActiveTab}
      className="space-y-4"
    >
      <TabsList className="grid w-full grid-cols-3 lg:w-[600px]">
        <TabsTrigger value="model-config">业务分析模型</TabsTrigger>
        <TabsTrigger value="collection-config">向量数据库</TabsTrigger>
        <TabsTrigger value="collection-data">数据管理</TabsTrigger>
      </TabsList>

      <TabsContent value="model-config" className="space-y-4">
        <Alert>
          <AlertDescription>
            在这里可以配置数据清洗功能支持的各种业务分析模型，包括模型名称、分析规则、验证指令等。
          </AlertDescription>
        </Alert>
        <ModelConfigTab />
      </TabsContent>

      <TabsContent value="collection-config" className="space-y-4">
        <Alert>
          <AlertDescription>
            在这里可以管理数据清洗功能使用的向量数据库中的 Collection 配置，包括字段定义、向量化设置等。
          </AlertDescription>
        </Alert>
        <CollectionConfigTab />
      </TabsContent>

      <TabsContent value="collection-data" className="space-y-4">
        <Alert>
          <AlertDescription>
            在这里可以管理和维护各个 Collection 中的实际数据，包括数据的查询、新增、删除等操作。通过向量搜索可以查找相似数据。
          </AlertDescription>
        </Alert>
        <CollectionDataTab />
      </TabsContent>
    </Tabs>
  );
}