import { apiRequest } from './api-client';
import {
  CollectionInfo,
  DataQuery,
  QueryResult,
  BatchDataInput,
  BatchDataDelete,
  BatchOperationResult,
} from '@/types/collection-manager';

export const collectionManagerApi = {
  /**
   * 获取Collection列表
   */
  getCollections: async (database: string, featureModule?: string) => {
    const params = new URLSearchParams();
    if (featureModule) {
      params.append('feature_module', featureModule);
    }

    return apiRequest<CollectionInfo[]>({
      method: 'GET',
      url: `/collection-manager/collections/${database}?${params}`,
    });
  },

  /**
   * 查询Collection中的数据
   */
  queryData: async (
    database: string,
    collectionName: string,
    query: DataQuery
  ) => {
    const params = new URLSearchParams({
      page: String(query.page),
      page_size: String(query.page_size),
    });

    if (query.search_field) {
      params.append('search_field', query.search_field);
    }
    if (query.search_text) {
      params.append('search_text', query.search_text);
    }
    if (query.top_k) {
      params.append('top_k', String(query.top_k));
    }

    return apiRequest<QueryResult>({
      method: 'GET',
      url: `/collection-manager/collections/${database}/${collectionName}/data?${params}`,
    });
  },

  /**
   * 批量插入或更新数据
   */
  batchInsertData: async (
    database: string,
    collectionName: string,
    data: BatchDataInput
  ) => {
    return apiRequest<BatchOperationResult>({
      method: 'POST',
      url: `/collection-manager/collections/${database}/${collectionName}/data`,
      data,
    });
  },

  /**
   * 批量删除数据
   */
  batchDeleteData: async (
    database: string,
    collectionName: string,
    data: BatchDataDelete
  ) => {
    return apiRequest<BatchOperationResult>({
      method: 'DELETE',
      url: `/collection-manager/collections/${database}/${collectionName}/data`,
      data,
    });
  },
};

// 导出服务
export * from './collection-manager';