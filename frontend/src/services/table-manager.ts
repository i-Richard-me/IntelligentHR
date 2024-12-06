import { apiRequest } from './api-client';
import {
  TableSchema,
  TableRecord,
  QueryResult,
  BatchOperationResult,
  OperationResponse,
} from '@/types/table-manager';

export const tableManagerApi = {
  /**
   * 获取表格结构
   */
  getTableSchema: async (database: string, tableName: string) => {
    return apiRequest<TableSchema>({
      method: 'GET',
      url: `/table-manager/tables/${database}/${tableName}/schema`,
    });
  },

  /**
   * 获取记录列表
   */
  listRecords: async (
    database: string,
    tableName: string,
    page: number = 1,
    pageSize: number = 10,
    sortField?: string,
    sortOrder?: 'asc' | 'desc'
  ) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      ...(sortField && { sort_field: sortField }),
      ...(sortOrder && { sort_order: sortOrder }),
    });

    return apiRequest<QueryResult>({
      method: 'GET',
      url: `/table-manager/tables/${database}/${tableName}/records?${params}`,
    });
  },

  /**
   * 获取单条记录
   */
  getRecord: async (database: string, tableName: string, recordId: string) => {
    return apiRequest<TableRecord>({
      method: 'GET',
      url: `/table-manager/tables/${database}/${tableName}/records/${recordId}`,
    });
  },

  /**
   * 创建记录
   */
  createRecords: async (
    database: string,
    tableName: string,
    records: Record<string, any>[]
  ) => {
    return apiRequest<BatchOperationResult>({
      method: 'POST',
      url: `/table-manager/tables/${database}/${tableName}/records`,
      data: { records },
    });
  },

  /**
   * 更新记录
   */
  updateRecord: async (
    database: string,
    tableName: string,
    recordId: string,
    data: Record<string, any>
  ) => {
    return apiRequest<TableRecord>({
      method: 'PUT',
      url: `/table-manager/tables/${database}/${tableName}/records/${recordId}`,
      data: { data },
    });
  },

  /**
   * 删除记录
   */
  deleteRecord: async (database: string, tableName: string, recordId: string) => {
    return apiRequest<OperationResponse>({
      method: 'DELETE',
      url: `/table-manager/tables/${database}/${tableName}/records/${recordId}`,
    });
  },

  /**
   * 批量创建或更新业务分析模型配置
   * @param database - 数据库名称（比如 "app_config"）
   * @param tableName - 表名（比如 "entity_configs"）
   * @param data - 要保存的数据
   */
  saveModelConfig: async (
    database: string,
    tableName: string,
    data: Record<string, any>
  ) => {
    return apiRequest<BatchOperationResult>({
      method: 'POST',
      url: `/table-manager/tables/${database}/${tableName}/records`,
      data: {
        records: [data],
      },
    });
  },

  /**
   * 获取所有业务分析模型配置
   * @param database - 数据库名称
   * @param tableName - 表名
   */
  getModelConfigs: async (database: string, tableName: string) => {
    return apiRequest<QueryResult>({
      method: 'GET',
      url: `/table-manager/tables/${database}/${tableName}/records`,
      params: {
        page: 1,
        page_size: 100, // 假设配置数量不会太多
      },
    });
  },
};

// 将这个API服务添加到统一导出中
export * from './table-manager';