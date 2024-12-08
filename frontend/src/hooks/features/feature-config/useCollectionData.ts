import { useState, useCallback, useEffect } from 'react';
import { CollectionConfig } from '@/types/table-manager';
import {
  DataQuery,
  QueryResult,
  BatchDataInput,
  BatchDataDelete,
  BatchOperationResult
} from '@/types/collection-manager';
import { collectionManagerApi } from '@/services/collection-manager';

interface UseCollectionDataProps {
  database?: string;
  collection?: CollectionConfig | null;
}

export function useCollectionData({ database = 'data_cleaning', collection }: UseCollectionDataProps) {
  const [data, setData] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // 查询数据
  const queryData = useCallback(async (query: DataQuery) => {
    if (!collection || !database) return;

    try {
      setLoading(true);
      setError(null);
      const response = await collectionManagerApi.queryData(
        database,
        collection.name,
        query
      );

      if (response.error) {
        throw new Error(response.error.detail);
      }

      setData(response.data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '查询数据失败';
      setError(new Error(errorMessage));
      console.error('Failed to query data:', error);
    } finally {
      setLoading(false);
    }
  }, [database, collection]);

  // 当数据库或Collection改变时，自动查询第一页数据
  useEffect(() => {
    if (database && collection) {
      queryData({
        page: 1,
        page_size: 10
      });
    }
  }, [database, collection, queryData]);

  // 批量插入或更新数据
  const batchInsert = useCallback(async (
    records: Record<string, any>[],
    updateStrategy: 'upsert' | 'skip' | 'error' = 'upsert'
  ): Promise<BatchOperationResult> => {
    if (!collection || !database) {
      throw new Error('未选择Collection');
    }

    try {
      setLoading(true);
      const response = await collectionManagerApi.batchInsertData(
        database,
        collection.name,
        {
          records,
          update_strategy: updateStrategy,
        }
      );

      if (response.error) {
        throw new Error(response.error.detail);
      }

      return response.data;
    } finally {
      setLoading(false);
    }
  }, [database, collection]);

  // 批量删除数据
  const batchDelete = useCallback(async (
    params: BatchDataDelete
  ): Promise<BatchOperationResult> => {
    if (!collection || !database) {
      throw new Error('未选择Collection');
    }

    try {
      setLoading(true);
      const response = await collectionManagerApi.batchDeleteData(
        database,
        collection.name,
        params
      );

      if (response.error) {
        throw new Error(response.error.detail);
      }

      return response.data;
    } finally {
      setLoading(false);
    }
  }, [database, collection]);

  // 构建表格列配置
  const getTableColumns = useCallback(() => {
    if (!collection) return [];

    return collection.fields.map(field => ({
      field: field.name,
      type: field.type,
      title: field.description || field.name,
      is_vector: field.is_vector
    }));
  }, [collection]);

  // 格式化数据
  const formatTableData = useCallback((rawData: QueryResult | null) => {
    if (!rawData || !collection) return [];

    return rawData.data.map(record => {
      // 初始化基础字段
      const formattedRow: Record<string, any> = {
        id: record.id,
      };

      // 处理嵌套的 data 对象中的字段
      if (record.data) {
        collection.fields.forEach(field => {
          const value = record.data[field.name];
          formattedRow[field.name] = formatFieldValue(value, field.type);
        });
      }

      // 添加相似度字段（如果存在）
      if (typeof record.distance === 'number') {
        formattedRow.distance = record.distance;
      }

      return formattedRow;
    });
  }, [collection]);

  return {
    data,
    loading,
    error,
    queryData,
    batchInsert,
    batchDelete,
    getTableColumns,
    formatTableData
  };
}

// 辅助函数：根据字段类型格式化值
function formatFieldValue(value: any, type: string): any {
  if (value === null || value === undefined) return '-';

  switch (type) {
    case 'text':
    case 'string':
    case 'str':
      return String(value);
    case 'int':
    case 'float':
      return Number(value);
    case 'boolean':
      return Boolean(value);
    case 'datetime':
      return new Date(value).toLocaleString();
    default:
      return value;
  }
}