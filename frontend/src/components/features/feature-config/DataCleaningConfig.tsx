'use client';

import { useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataCleaningTypeTab } from './DataCleaningTypeTab';
import { VectorCollectionTab } from './VectorCollectionTab';
import { VectorDataTab } from './VectorDataTab';

export function DataCleaningConfig() {
  const [activeTab, setActiveTab] = useState('model-config');

  return (
    <Tabs
      defaultValue="model-config"
      value={activeTab}
      onValueChange={setActiveTab}
      className="space-y-4"
    >
      <TabsList className="inline-grid grid-cols-3 mx-auto">
        <TabsTrigger value="model-config">数据清洗类型</TabsTrigger>
        <TabsTrigger value="collection-config">向量数据库</TabsTrigger>
        <TabsTrigger value="collection-data">数据管理</TabsTrigger>
      </TabsList>

      <TabsContent value="model-config" className="space-y-4">
        <Alert>
          <AlertDescription>
            在这里可以配置数据清洗功能支持的各种数据类型，包括类型名称、清洗规则、验证指令等。
          </AlertDescription>
        </Alert>
        <DataCleaningTypeTab />
      </TabsContent>

      <TabsContent value="collection-config" className="space-y-4">
        <Alert>
          <AlertDescription>
            在这里可以管理数据清洗功能使用的向量数据库中的 Collection 配置，包括字段定义、向量化设置等。
          </AlertDescription>
        </Alert>
        <VectorCollectionTab />
      </TabsContent>

      <TabsContent value="collection-data" className="space-y-4">
        <Alert>
          <AlertDescription>
            在这里可以管理和维护各个 Collection 中的实际数据，包括数据的查询、新增、删除等操作。通过向量搜索可以查找相似数据。
          </AlertDescription>
        </Alert>
        <VectorDataTab />
      </TabsContent>
    </Tabs>
  );
}