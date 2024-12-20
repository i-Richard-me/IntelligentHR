// src/types/api.ts

/**
 * 任务状态枚举
 */
export enum TaskStatus {
  WAITING = "waiting",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled"
}

/**
 * 任务创建请求参数
 */
export interface TaskCreateRequest {
  file: File;
  context: string;
}

/**
 * 文本分类任务创建请求参数
 */
export interface ClassificationTaskCreateRequest {
  file: File;
  context: string;
  categories: Record<string, string>;
  is_multi_label: boolean;
}

/**
 * 任务详情响应
 */
export interface TaskResponse {
  task_id: string;
  user_id: string;
  status: TaskStatus;
  context: string;
  source_file_url: string;
  result_file_url: string | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  total_records: number | null;
  processed_records: number | null;
  progress: string;
  cancellation_requested: boolean;
  cancelled_at: string | null;
}

/**
 * 文本分类任务响应
 */
export interface ClassificationTaskResponse extends TaskResponse {
  categories: Record<string, string>;
  is_multi_label: boolean;
}

/**
 * API 错误响应
 */
export interface ApiError {
  detail: string;
  status_code?: number;
}