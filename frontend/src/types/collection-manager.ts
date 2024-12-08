// Collection数据查询参数
export interface DataQuery {
  page: number;
  page_size: number;
  search_field?: string;
  search_text?: string;
  top_k?: number;
}

// Collection中的单条数据记录
export interface DataRecord {
  id?: string;
  data: Record<string, any>;
  distance?: number;
}

// 查询结果
export interface QueryResult {
  total: number;
  page: number;
  page_size: number;
  data: DataRecord[];
}

// 批量数据操作输入
export interface BatchDataInput {
  records: Record<string, any>[];
  update_strategy: 'upsert' | 'skip' | 'error';
}

// 批量数据删除参数
export interface BatchDataDelete {
  ids?: string[];
  filter_conditions?: Record<string, any>;
}

// 批量操作结果
export interface BatchOperationResult {
  success_count: number;
  error_count: number;
  errors?: Array<{
    data: Record<string, any>;
    error: string;
  }>;
}

// Collection信息
export interface CollectionInfo {
  name: string;
  display_name?: string;
  description?: string;
  total_records: number;
  feature_modules: string[];
  created_at: string;
  updated_at: string;
}