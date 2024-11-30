// src/services/api-client.ts

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import { ApiError, ApiResponse } from '@/types/common';

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000, // 30 秒超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 这里可以添加认证信息，例如：
    const userId = localStorage.getItem('userId');
    if (userId) {
      config.headers['X-User-Id'] = userId;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<ApiError>) => {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || '请求失败，请稍后重试',
      status_code: error.response?.status
    };
    return Promise.reject(apiError);
  }
);

// API 请求包装函数
export const apiRequest = async <T>(
  config: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
      const response = await apiClient(config);
      console.log('Raw API response:', response);
      // 直接返回 response 作为 data
      return { data: response as T };
  } catch (error) {
      console.error('API error:', error);
      if (error instanceof Error) {
          return { 
              data: null as T, 
              error: {
                  detail: error.message,
                  status_code: (error as any).response?.status
              }
          };
      }
      throw error;
  }
};