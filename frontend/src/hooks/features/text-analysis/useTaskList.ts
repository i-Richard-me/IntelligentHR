import { useState, useCallback } from 'react';
import { TaskResponse } from '@/types/api';
import { textAnalysisApi } from '@/services';
import { useToast } from '@/hooks/use-toast';

export function useTaskList() {
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const { toast } = useToast();

  const fetchTasks = useCallback(async () => {
    try {
        setLoading(true);
        setError(null);
        const response = await textAnalysisApi.getTasks();
        console.log('Task list response:', response); // 添加响应日志
        if (response.data) {
            console.log('Setting tasks:', response.data); // 添加设置数据日志
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

  return {
    tasks,
    loading,
    error,
    fetchTasks,
  };
}