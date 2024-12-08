import { useState, useCallback, useEffect } from 'react';
import { CollectionConfig } from '@/types/table-manager';
import { tableManagerApi } from '@/services';

// 常量定义
const DATABASE = 'app_config_db';
const TABLE_NAME = 'collection_config';
const FEATURE_MODULE = 'data_cleaning';  // 固定为数据清洗功能模块

export function useCollectionConfigs() {
  const [configs, setConfigs] = useState<CollectionConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // 获取配置列表
  const fetchConfigs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await tableManagerApi.listRecords(DATABASE, TABLE_NAME);

      if (response.error) {
        throw new Error(response.error.detail);
      }

      // 将数据转换为 CollectionConfig 类型，并只保留属于数据清洗功能的配置
      const collectionConfigs: CollectionConfig[] = response.data.data
        .map(record => ({
          name: record.data.name,
          display_name: record.data.display_name,
          description: record.data.description,
          fields: record.data.fields || [],
          embedding_fields: record.data.embedding_fields || [],
          collection_databases: record.data.collection_databases || [],
          feature_modules: record.data.feature_modules || [],
          created_at: record.created_at,
          updated_at: record.updated_at,
        }))
        .filter(config => config.feature_modules.includes(FEATURE_MODULE));

      setConfigs(collectionConfigs);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取配置列表失败';
      setError(new Error(errorMessage));
      console.error('Failed to fetch configs:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 创建配置
  const createConfig = useCallback(async (data: Partial<CollectionConfig>) => {
    try {
      const response = await tableManagerApi.createRecords(DATABASE, TABLE_NAME, [data]);

      if (response.error) {
        throw new Error(response.error.detail);
      }

      if (response.data.error_count > 0 && response.data.errors?.[0]) {
        throw new Error(response.data.errors[0].error || '创建失败');
      }

      return response.data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '创建配置失败';
      console.error('Failed to create config:', error);
      throw new Error(errorMessage);
    }
  }, []);

  // 更新配置
  const updateConfig = useCallback(async (name: string, data: Partial<CollectionConfig>) => {
    try {
      const response = await tableManagerApi.updateRecord(
        DATABASE,
        TABLE_NAME,
        name,  // 使用 name 作为主键
        data
      );

      if (response.error) {
        throw new Error(response.error.detail);
      }

      return response.data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '更新配置失败';
      console.error('Failed to update config:', error);
      throw new Error(errorMessage);
    }
  }, []);

  // 删除配置
  const deleteConfig = useCallback(async (name: string) => {
    try {
      const response = await tableManagerApi.deleteRecord(
        DATABASE,
        TABLE_NAME,
        name  // 使用 name 作为主键
      );

      if (response.error) {
        throw new Error(response.error.detail);
      }

      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '删除配置失败';
      console.error('Failed to delete config:', error);
      throw new Error(errorMessage);
    }
  }, []);

  // 获取表结构
  const getSchema = useCallback(async () => {
    try {
      const response = await tableManagerApi.getTableSchema(DATABASE, TABLE_NAME);

      if (response.error) {
        throw new Error(response.error.detail);
      }

      return response.data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取表结构失败';
      console.error('Failed to get schema:', error);
      throw new Error(errorMessage);
    }
  }, []);

  // 初始加载
  useEffect(() => {
    fetchConfigs();
  }, [fetchConfigs]);

  return {
    configs,
    loading,
    error,
    refresh: fetchConfigs,
    createConfig,
    updateConfig,
    deleteConfig,
    getSchema,
  };
}