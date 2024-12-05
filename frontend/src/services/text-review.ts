import { apiRequest } from './api-client';
import { TaskCreateRequest, TaskResponse } from '@/types/api';

export const textReviewApi = {
  /**
   * 创建文本评估任务
   */
  createTask: async (data: TaskCreateRequest) => {
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('context', data.context);

    return apiRequest<TaskResponse>({
      method: 'POST',
      url: '/text-review/tasks',
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
      url: `/text-review/tasks/${taskId}`,
    });
  },

  /**
   * 获取任务列表
   */
  getTasks: async () => {
    return apiRequest<TaskResponse[]>({
        method: 'GET',
        url: '/text-review/tasks',
    });
},

  /**
   * 下载评估结果
   */
  downloadResult: async (taskId: string, fileName: string) => {
    const response = await apiRequest<Blob>({
      method: 'GET',
      url: `/text-review/tasks/${taskId}/download`,
      responseType: 'blob',
    });

    const url = window.URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${fileName}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  async cancelTask(taskId: string) {
    return apiRequest<TaskResponse>({
      method: 'POST',
      url: `/text-review/tasks/${taskId}/cancel`,
    });
  },
};