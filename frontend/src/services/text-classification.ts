import { apiRequest } from './api-client';
import { ClassificationTaskCreateRequest, ClassificationTaskResponse } from '@/types/api';

export const textClassificationApi = {
  /**
   * 创建文本分类任务
   */
  createTask: async (data: ClassificationTaskCreateRequest) => {
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('context', data.context);
    formData.append('categories', JSON.stringify(data.categories));
    formData.append('is_multi_label', String(data.is_multi_label));

    return apiRequest<ClassificationTaskResponse>({
      method: 'POST',
      url: '/text-classification/tasks',
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
    return apiRequest<ClassificationTaskResponse>({
      method: 'GET',
      url: `/text-classification/tasks/${taskId}`,
    });
  },

  /**
   * 获取任务列表
   */
  getTasks: async () => {
    return apiRequest<ClassificationTaskResponse[]>({
      method: 'GET',
      url: '/text-classification/tasks',
    });
  },

  /**
   * 下载分析结果
   */
  downloadResult: async (taskId: string, fileName: string) => {
    const response = await apiRequest<Blob>({
      method: 'GET',
      url: `/text-classification/tasks/${taskId}/download`,
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
};