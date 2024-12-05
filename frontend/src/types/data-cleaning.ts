/**
 * 实体配置类型
 */
export interface EntityConfig {
  entity_type: string;
  display_name: string;
  description: string | null;
  validation_instructions: string;
  analysis_instructions: string;
  verification_instructions: string;
  collection_name: string;
}

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
  entity_type: string;
  search_enabled?: boolean;
  retrieval_enabled?: boolean;
}

/**
 * 任务详情响应
 */
export interface TaskResponse {
  task_id: string;
  user_id: string;
  status: TaskStatus;
  entity_type: string;
  source_file_url: string;
  result_file_url: string | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  total_records: number | null;
  processed_records: number | null;
  progress: string;
  search_enabled: 'enabled' | 'disabled';
  retrieval_enabled: 'enabled' | 'disabled';
  cancellation_requested: boolean;
  cancelled_at: string | null;
}

/**
 * 实体配置响应
 */
export interface EntityConfigResponse extends EntityConfig {}

/**
 * 实体清洗选项
 */
export interface CleaningOptions {
  search_enabled: boolean;
  retrieval_enabled: boolean;
}