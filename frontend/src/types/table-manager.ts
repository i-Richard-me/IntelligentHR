/**
 * 表格字段定义
 */
export interface TableField {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
  default?: any;
  max_length?: number;
  description?: string;
}

/**
 * 表格结构信息
 */
export interface TableSchema {
  table_name: string;
  fields: TableField[];
  primary_keys: string[];
  description?: string;
}

/**
 * 排序方向
 */
export type SortOrder = 'asc' | 'desc';

/**
 * 分页参数
 */
export interface PaginationParams {
  page: number;
  page_size: number;
}

/**
 * 表格记录
 */
export interface TableRecord {
  id?: string | number;
  created_at?: string;
  updated_at?: string;
  data: Record<string, any>;
}

/**
 * 查询结果
 */
export interface QueryResult {
  total: number;
  page: number;
  page_size: number;
  data: TableRecord[];
}

/**
 * 批量操作结果
 */
export interface BatchOperationResult {
  success_count: number;
  error_count: number;
  errors?: Array<{
    data: Record<string, any>;
    error: string;
  }>;
}

/**
 * 操作结果
 */
export interface OperationResponse {
  success: boolean;
  message: string;
  data?: any;
}

/**
 * 数据校验规则类型
 */
export interface ValidationRule {
  type: 'required' | 'maxLength' | 'pattern';
  message: string;
  value?: any;
}

/**
 * 表单字段定义
 */
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'number' | 'select' | 'switch';
  placeholder?: string;
  defaultValue?: any;
  options?: Array<{
    label: string;
    value: any;
  }>;
  rules?: ValidationRule[];
  description?: string;
}

/**
 * 业务分析模型配置
 */
export interface AnalysisModelConfig {
  entity_type: string;
  display_name: string;
  description?: string;
  validation_instructions: string;
  analysis_instructions: string;
  verification_instructions: string;
  collection_name: string;
}

/**
 * Collection 字段配置
 */
export interface CollectionFieldConfig {
  name: string;
  type: string;
  description?: string; // 修改为可选
  is_vector: boolean;
}

/**
 * Collection 配置信息
 */
export interface CollectionConfig {
  name: string;
  display_name?: string;
  description?: string;
  fields: CollectionFieldConfig[];
  embedding_fields: string[];
  collection_databases: string[];
  feature_modules: string[];
  created_at?: string;
  updated_at?: string;
}