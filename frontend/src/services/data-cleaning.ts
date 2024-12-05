import { apiRequest } from './api-client';
import {
  TaskCreateRequest,
  TaskResponse,
  EntityConfigResponse
} from '@/types/data-cleaning';

export const dataCleaningApi = {
  /**
   * 获取支持的实体类型列表
   */
  getEntityTypes: async () => {
    return apiRequest<EntityConfigResponse[]>({
      method: 'GET',
      url: '/data-cleaning/entity-types',
    });
  },

  /**
   * 创建数据清洗任务
   */
  createTask: async (data: TaskCreateRequest) => {
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('entity_type', data.entity_type);
    formData.append('search_enabled', String(data.search_enabled ?? true));
    formData.append('retrieval_enabled', String(data.retrieval_enabled ?? true));

    return apiRequest<TaskResponse>({
      method: 'POST',
      url: '/data-cleaning/tasks',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  /**
   * 获取任务状态
   */
  getTaskStatus: async (taskId: string) => {
    return apiRequest<TaskResponse>({
      method: 'GET',
      url: `/data-cleaning/tasks/${taskId}`,
    });
  },

  /**
   * 获取任务列表
   */
  getTasks: async () => {
    return apiRequest<TaskResponse[]>({
      method: 'GET',
      url: '/data-cleaning/tasks',
    });
  },

  /**
   * 下载清洗结果
   */
  downloadResult: async (taskId: string, fileName: string) => {
    const response = await apiRequest<Blob>({
      method: 'GET',
      url: `/data-cleaning/tasks/${taskId}/download`,
      responseType: 'blob',
    });

    // 创建并触发下载
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${fileName}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  /**
   * 取消任务
   */
  cancelTask: async (taskId: string) => {
    return apiRequest<TaskResponse>({
      method: 'POST',
      url: `/data-cleaning/tasks/${taskId}/cancel`,
    });
  },
};