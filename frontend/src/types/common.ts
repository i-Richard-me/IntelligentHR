// src/types/common.ts

/**
 * API 错误响应
 */
export interface ApiError {
  detail: string;
  status_code?: number;
}


/**
 * 通用响应格式
 */
export interface ApiResponse<T> {
  data: T;
  error?: ApiError;
}

/**
 * 分页参数
 */
export interface PaginationParams {
  page: number;
  page_size: number;
}

/**
 * 分页响应
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * 排序参数
 */
export interface SortParams {
  sort_by: string;
  order: 'asc' | 'desc';
}

/**
 * 文件上传状态
 */
export interface FileUploadStatus {
  progress: number;
  status: 'idle' | 'uploading' | 'success' | 'error';
  error?: string;
}

/**
 * 任务进度状态
 */
export interface TaskProgress {
  current: number;
  total: number | null;
  percentage: number;
}

/**
 * 用户设置
 */
export interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  language: 'zh' | 'en';
}