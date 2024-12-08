import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql import select, and_
from sqlalchemy import Table, Column, Integer, String, Text, JSON, DateTime, text, func
from datetime import datetime
import asyncio

from ..exceptions.collection_exceptions import (
    CollectionNotFoundError,
    DatabaseCollectionNotFoundError,
    InvalidDataError,
    VectorizeError,
    BatchOperationError,
)
from ..models.schemas import (
    CollectionConfig,
    DataQuery,
    BatchDataInput,
    BatchDataDelete,
    QueryResult,
    BatchOperationResult,
)
from common.utils.vector_db_utils import (
    async_connect_to_milvus,
    async_initialize_vector_store,
    async_search_in_milvus,
    async_insert_to_milvus,
    async_update_milvus_records,
    async_delete_from_milvus,
    async_get_collection_stats,
    async_get_actual_count
)
from common.utils.llm_tools import CustomEmbeddings
from common.database.base import CollectionBase, get_table_args
from config.config import config

logger = logging.getLogger(__name__)


class CollectionConfigTable(CollectionBase):
    """Collection配置表模型"""
    __tablename__ = 'collection_config'
    __table_args__ = get_table_args()

    id = Column(Integer, primary_key=True, comment='主键ID')
    name = Column(String(100), nullable=False, unique=True, comment='Collection名称')
    display_name = Column(String(100), comment='显示名称')
    description = Column(Text, comment='Collection描述')
    fields = Column(JSON, nullable=False, comment='字段配置')
    embedding_fields = Column(JSON, nullable=False, comment='需要向量化的字段列表')
    collection_databases = Column(JSON, nullable=False, comment='包含该Collection的数据库列表')
    feature_modules = Column(JSON, comment='所属功能模块列表')
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        onupdate=func.now(),  # 使用 SQLAlchemy func
        comment='更新时间'
    )

class CollectionService:
    """Collection管理服务类"""

    def __init__(self, embedding_model: str = "BAAI/bge-m3", vector_dim: int = 1024):
        """初始化服务
        
        Args:
            embedding_model: 向量化模型名称
            vector_dim: 向量维度
        """
        self.vector_dim = vector_dim
        self.embeddings = CustomEmbeddings(
            model=embedding_model,
            # api_key=config.embedding.api_key,
            # api_url=config.embedding.api_url
        )
        logger.info(f"CollectionService initialized with model: {embedding_model}")

    async def get_collections(self, db: Session, database: str, feature_module: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取指定数据库可用的collection列表
        
        Args:
            db: 数据库会话
            database: 数据库名称
            feature_module: 功能模块名称，用于过滤collection
            
        Returns:
            List[Dict[str, Any]]: Collection列表
        """
        # 获取所有collections
        query = select(CollectionConfigTable)
        collections = db.execute(query).scalars().all()
        
        result = []
        for collection in collections:
            # 检查数据库是否在允许列表中
            if database in collection.collection_databases:
                # 如果指定了功能模块，检查是否属于该模块
                if feature_module and feature_module not in collection.feature_modules:
                    continue
                    
                try:
                    await async_connect_to_milvus(database)
                    collection_obj = await async_initialize_vector_store(collection.name)
                    stats = await async_get_collection_stats(collection_obj)
                    
                    result.append({
                        "name": collection.name,
                        "display_name": collection.display_name,
                        "description": collection.description,
                        "total_records": stats["实体数量"],
                        "feature_modules": collection.feature_modules,
                        "created_at": collection.created_at,
                        "updated_at": collection.updated_at
                    })
                except Exception as e:
                    logger.error(f"Failed to get stats for collection {collection.name}: {str(e)}")
                    result.append({
                        "name": collection.name,
                        "display_name": collection.display_name,
                        "description": collection.description,
                        "total_records": 0,
                        "feature_modules": collection.feature_modules,
                        "created_at": collection.created_at,
                        "updated_at": collection.updated_at
                    })
                    
        return result

    async def query_collection_data(
        self,
        db: Session,
        database: str,
        collection_name: str,
        query_params: DataQuery
    ) -> QueryResult:
        """查询collection数据"""
        # 验证collection配置
        config = await self._get_collection_config(db, collection_name)
        if database not in config.collection_databases:
            raise DatabaseCollectionNotFoundError(database, collection_name)

        await async_connect_to_milvus(database)
        collection = await async_initialize_vector_store(collection_name)
        
        try:
            # 获取实际的记录总数
            total_records = await async_get_actual_count(collection)
            
            if query_params.search_field and query_params.search_text:
                # 向量相似度搜索
                if query_params.search_field not in config.embedding_fields:
                    raise InvalidDataError(f"Field {query_params.search_field} is not configured for vector search")
                
                # 生成查询向量
                query_vector = await self._generate_vector(query_params.search_text)
                
                results = await async_search_in_milvus(
                    collection,
                    query_vector,
                    query_params.search_field,
                    query_params.top_k
                )
            else:
                # 普通分页查询
                offset = (query_params.page - 1) * query_params.page_size
                expr = ""  # 可以添加其他过滤条件
                
                # 使用普通查询而不是向量搜索
                output_fields = [field.name for field in collection.schema.fields 
                               if not field.name.endswith("_vector")]
                results = await asyncio.to_thread(
                    collection.query,
                    expr=expr,
                    output_fields=output_fields,
                    offset=offset,
                    limit=query_params.page_size
                )
                
                # 添加distance字段（普通查询时为0）
                for result in results:
                    result["distance"] = 0.0
            
            # 格式化结果为符合DataRecord模型的格式
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": str(result.get("id", "")),
                    "data": result,
                    "distance": result.get("distance", 0.0)
                })
            
            return QueryResult(
                total=total_records,
                page=query_params.page,
                page_size=query_params.page_size,
                data=formatted_results
            )
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise BatchOperationError("query", str(e))
            

    async def batch_insert_data(
        self,
        db: Session,
        database: str,
        collection_name: str,
        input_data: BatchDataInput
    ) -> BatchOperationResult:
        """批量插入数据
        
        Args:
            db: 数据库会话
            database: 数据库名称
            collection_name: Collection名称
            input_data: 输入数据
            
        Returns:
            BatchOperationResult: 操作结果
        """
        # 验证collection配置
        config = await self._get_collection_config(db, collection_name)
        if database not in config.collection_databases:
            raise DatabaseCollectionNotFoundError(database, collection_name)

        # 准备向量数据
        vectors = {}
        for field in config.embedding_fields:
            try:
                field_values = [record[field] for record in input_data.records]
                vectors[field] = await self._batch_generate_vectors(field_values)
            except Exception as e:
                raise VectorizeError(field, str(e))

        try:
            await async_connect_to_milvus(database)
            collection = await async_initialize_vector_store(collection_name)
            
            if input_data.update_strategy == "upsert":
                await async_update_milvus_records(
                    collection,
                    input_data.records,
                    vectors,
                    config.embedding_fields
                )
            else:
                await async_insert_to_milvus(
                    collection,
                    input_data.records,
                    vectors
                )
            
            return BatchOperationResult(
                success_count=len(input_data.records),
                error_count=0
            )
            
        except Exception as e:
            logger.error(f"Batch insert failed: {str(e)}")
            raise BatchOperationError("insert", str(e))

    async def batch_delete_data(
        self,
        db: Session,
        database: str,
        collection_name: str,
        delete_data: BatchDataDelete
    ) -> BatchOperationResult:
        """批量删除数据
        
        Args:
            db: 数据库会话
            database: 数据库名称
            collection_name: Collection名称
            delete_data: 删除条件
            
        Returns:
            BatchOperationResult: 操作结果
        """
        # 验证collection配置
        config = await self._get_collection_config(db, collection_name)
        if database not in config.collection_databases:
            raise DatabaseCollectionNotFoundError(database, collection_name)

        try:
            await async_connect_to_milvus(database)
            collection = await async_initialize_vector_store(collection_name)
            
            # 构删除表达式
            if delete_data.ids:
                # Convert string IDs to integers for Milvus
                int_ids = [int(id_str) for id_str in delete_data.ids]
                expr = f"id in {int_ids}"
            elif delete_data.filter_conditions:
                conditions = []
                for field, value in delete_data.filter_conditions.items():
                    conditions.append(f"{field} == '{value}'")
                expr = " && ".join(conditions)
            else:
                raise InvalidDataError("Must provide either ids or filter_conditions")
            
            # 执行删除
            deleted_count = await async_delete_from_milvus(collection, expr)
            
            return BatchOperationResult(
                success_count=deleted_count,
                error_count=0
            )
            
        except Exception as e:
            logger.error(f"Batch delete failed: {str(e)}")
            raise BatchOperationError("delete", str(e))

    async def _get_collection_config(
        self,
        db: Session,
        collection_name: str
    ) -> CollectionConfig:
        """获取collection配置
        
        Args:
            db: 数据库会话
            collection_name: Collection名称
            
        Returns:
            CollectionConfig: Collection配置信息
            
        Raises:
            CollectionNotFoundError: 当Collection不存在时抛出
        """
        query = select(CollectionConfigTable).where(
            CollectionConfigTable.name == collection_name
        )
        result = db.execute(query).scalar_one_or_none()
        
        if not result:
            raise CollectionNotFoundError(collection_name, "any")
            
        return CollectionConfig(
            name=result.name,
            description=result.description,
            fields=result.fields,
            embedding_fields=result.embedding_fields,
            collection_databases=result.collection_databases
        )

    async def _generate_vector(self, text: str) -> List[float]:
        """生成文本向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 向量数据
        """
        try:
            return self.embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"Vector generation failed: {str(e)}")
            raise VectorizeError("text", str(e))

    async def _batch_generate_vectors(self, texts: List[str]) -> List[List[float]]:
        """批量生成文本向量
        
        Args:
            texts: 输入文本列表
            
        Returns:
            List[List[float]]: 向量数据列表
        """
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as e:
            logger.error(f"Batch vector generation failed: {str(e)}")
            raise VectorizeError("texts", str(e))