"""
检索工具模块，提供向量数据库检索功能
"""
from typing import List, Dict, Optional
from common.utils.llm_tools import CustomEmbeddings
from common.utils.vector_db_utils import (
    connect_to_milvus,
    initialize_vector_store,
    asearch_in_milvus,
)
import logging

logger = logging.getLogger(__name__)

# 统一字段名称常量
ORIGINAL_NAME_FIELD = "original_name"
STANDARD_NAME_FIELD = "standard_name"

class RetrievalTools:
    """向量检索工具类 - 单例模式"""
    _instances = {}

    def __new__(cls, collection_name: str, db_name: str = "default", embedding_config: Optional[Dict] = None):
        """创建或获取已存在的实例"""
        instance_key = f"{db_name}:{collection_name}"
        if instance_key not in cls._instances:
            instance = super(RetrievalTools, cls).__new__(cls)
            instance.collection_name = collection_name
            instance.db_name = db_name
            instance._embedding_config = embedding_config or {}
            instance.collection = None
            cls._instances[instance_key] = instance
            
        return cls._instances[instance_key]

    def _initialize_collection(self):
        """初始化 Milvus 集合"""
        try:
            connect_to_milvus(self.db_name)
            collection = initialize_vector_store(self.collection_name)
            logger.info(f"成功初始化collection: {self.collection_name}")
            return collection
        except Exception as e:
            logger.error(f"初始化collection失败: {str(e)}")
            raise

    async def aretrieve(self, query: str, top_k: int = 1) -> List[Dict]:
        """异步执行实体检索"""
        try:
            # 延迟初始化collection
            if self.collection is None:
                self.collection = self._initialize_collection()

            # 初始化嵌入模型
            embedding_model = CustomEmbeddings(**self._embedding_config)

            # 生成查询向量
            query_embedding = await embedding_model.aembed_query(query)

            # 执行向量检索，移除output_fields参数
            results = await asearch_in_milvus(
                collection=self.collection,
                query_vector=query_embedding,
                vector_field=ORIGINAL_NAME_FIELD,
                top_k=top_k
            )

            # 处理检索结果
            retrieved_entities = []
            for result in results:
                entity = {
                    ORIGINAL_NAME_FIELD: result.get(ORIGINAL_NAME_FIELD),
                    STANDARD_NAME_FIELD: result.get(STANDARD_NAME_FIELD),
                    "distance": result.get("distance"),
                }
                retrieved_entities.append(entity)

            logger.debug(f"检索成功: query={query}, results={len(retrieved_entities)}")
            return retrieved_entities

        except Exception as e:
            logger.error(f"实体检索失败: query={query}, error={str(e)}")
            raise