import { useState, useCallback } from 'react';
import { TaskResponse, EntityConfigResponse } from '@/types/data-cleaning';
import { dataCleaningApi } from '@/services';
import { useToast } from '@/hooks/use-toast';

export function useCleaningTaskList() {
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [entityTypes, setEntityTypes] = useState<EntityConfigResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const { toast } = useToast();

  const fetchEntityTypes = useCallback(async () => {
    try {
      const response = await dataCleaningApi.getEntityTypes();
      if (response.data) {
        setEntityTypes(response.data);
      }
    } catch (error) {
      console.error('Entity types fetch error:', error);
      const errorMessage = error instanceof Error ? error.message : '获取实体类型失败';
      toast({
        variant: 'destructive',
        title: '获取实体类型失败',
        description: errorMessage,
      });
    }
  }, [toast]);

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await dataCleaningApi.getTasks();

      if (response.data) {
        setTasks(response.data);
      }
    } catch (error) {
      console.error('Task list error:', error);
      const errorMessage = error instanceof Error ? error.message : '请稍后重试';
      setError(new Error(errorMessage));
      toast({
        variant: 'destructive',
        title: '获取任务列表失败',
        description: errorMessage,
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const createTask = useCallback(async (
    file: File,
    entity_type: string,
    options?: { search_enabled?: boolean; retrieval_enabled?: boolean }
  ) => {
    try {
      setLoading(true);
      const response = await dataCleaningApi.createTask({
        file,
        entity_type,
        ...options
      });

      if (response.data) {
        toast({
          title: '创建成功',
          description: '数据清洗任务已开始处理',
        });
        await fetchTasks(); // 刷新任务列表
        return response.data;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '创建任务失败';
      toast({
        variant: 'destructive',
        title: '创建失败',
        description: errorMessage,
      });
      throw error;
    } finally {
      setLoading(false);
    }
  }, [fetchTasks, toast]);

  const downloadResult = useCallback(async (taskId: string, fileName: string) => {
    try {
      await dataCleaningApi.downloadResult(taskId, fileName);
    } catch (error) {
      console.error('Download failed:', error);
      const errorMessage = error instanceof Error ? error.message : '下载失败';
      toast({
        variant: 'destructive',
        title: '下载失败',
        description: errorMessage,
      });
    }
  }, [toast]);

  return {
    tasks,
    entityTypes,
    loading,
    error,
    fetchTasks,
    fetchEntityTypes,
    createTask,
    downloadResult,
  };
}