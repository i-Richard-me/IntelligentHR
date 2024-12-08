import { useState, useCallback, useEffect } from 'react';
import { AnalysisModelConfig } from '@/types/table-manager';
import { tableManagerApi } from '@/services';

// 常量定义
const DATABASE = 'app_config_db';
const TABLE_NAME = 'entity_configs';

export function useDataCleaningTypes() {
  const [configs, setConfigs] = useState<AnalysisModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // 获取配置列表
  const fetchConfigs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await tableManagerApi.getModelConfigs(DATABASE, TABLE_NAME);

      if (response.error) {
        throw new Error(response.error.detail);
      }

      // 确保转换后的数据符合 AnalysisModelConfig 类型
      const modelConfigs: AnalysisModelConfig[] = response.data.data.map(record => ({
        entity_type: record.data.entity_type,
        display_name: record.data.display_name,
        description: record.data.description,
        validation_instructions: record.data.validation_instructions,
        analysis_instructions: record.data.analysis_instructions,
        verification_instructions: record.data.verification_instructions,
        collection_name: record.data.collection_name,
      }));

      setConfigs(modelConfigs);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取配置列表失败';
      setError(new Error(errorMessage));
      console.error('Failed to fetch configs:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 创建配置
  const createConfig = useCallback(async (data: Partial<AnalysisModelConfig>) => {
    try {
      const response = await tableManagerApi.saveModelConfig(DATABASE, TABLE_NAME, data);

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
  const updateConfig = useCallback(async (entityType: string, data: Partial<AnalysisModelConfig>) => {
    try {
      const response = await tableManagerApi.updateRecord(
        DATABASE,
        TABLE_NAME,
        entityType,
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
  const deleteConfig = useCallback(async (entityType: string) => {
    try {
      const response = await tableManagerApi.deleteRecord(
        DATABASE,
        TABLE_NAME,
        entityType
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

  // 初始加载
  useEffect(() => {
    fetchConfigs();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    configs,
    loading,
    error,
    refresh: fetchConfigs,
    createConfig,
    updateConfig,
    deleteConfig,
  };
}