"""
检索工具模块，提供向量数据库检索功能
"""
from typing import List, Dict, Optional, Callable
from common.utils.llm_tools import CustomEmbeddings
from common.utils.vector_db_utils import (
    connect_to_milvus,
    initialize_vector_store,
    asearch_in_milvus,
)
import os


class RetrievalTools:
    """向量检索工具类"""

    def __init__(
            self,
            collection_name: str,
            db_name: str = "default",
            embedding_config: Optional[Dict] = None
    ):
        """
        初始化检索工具

        Args:
            collection_name: Milvus集合名称
            db_name: 数据库名称
            embedding_config: 嵌入模型配置
        """
        self.collection_name = collection_name
        self.db_name = db_name
        self._embedding_config = embedding_config or {
            "api_key": os.getenv("EMBEDDING_API_KEY", ""),
            "api_url": os.getenv("EMBEDDING_API_BASE", ""),
            "model": os.getenv("EMBEDDING_MODEL", ""),
        }
        self.collection = self._initialize_collection()

    def _initialize_collection(self):
        """初始化 Milvus 集合"""
        connect_to_milvus(self.db_name)
        return initialize_vector_store(self.collection_name)

    def _get_field_names(self):
        """获取集合字段名称"""
        fields = [field.name for field in self.collection.schema.fields]
        original_name_field = (
            "company_name" if "company_name" in fields else "school_name"
        )
        standard_name_field = (
            "standard_name" if "standard_name" in fields else original_name_field
        )
        return original_name_field, standard_name_field

    async def aretrieve(self, query: str, top_k: int = 1) -> List[Dict]:
        """
        异步执行实体检索

        Args:
            query: 检索查询
            top_k: 返回结果数量

        Returns:
            检索结果列表，包含原始名称、标准名称和相似度距离
        """
        # 初始化嵌入模型
        embedding_model = CustomEmbeddings(**self._embedding_config)

        # 生成查询向量
        query_embedding = await embedding_model.aembed_query(query)

        # 获取字段名称
        original_name_field, standard_name_field = self._get_field_names()

        # 执行向量检索
        results = await asearch_in_milvus(
            self.collection,
            query_embedding,
            original_name_field,
            top_k
        )

        # 处理检索结果
        retrieved_entities = []
        for result in results:
            entity = {
                "original_name": result.get(original_name_field),
                "standard_name": result.get(standard_name_field),
                "distance": result.get("distance"),
            }
            retrieved_entities.append(entity)

        return retrieved_entities