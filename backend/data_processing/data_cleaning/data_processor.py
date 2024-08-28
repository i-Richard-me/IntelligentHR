import os
from typing import List, Dict, Callable
from pymilvus import (
    connections,
    Collection,
    utility,
)

from utils.llm_tools import CustomEmbeddings


def connect_to_milvus():
    """连接到 Milvus 数据库"""
    connections.connect(
        alias="default",
        host=os.getenv("VECTOR_DB_HOST", "localhost"),
        port=os.getenv("VECTOR_DB_PORT", "19530"),
        db_name=os.getenv("VECTOR_DB_DATA_CLEANING", "default"),
    )


def initialize_vector_store(collection_name: str) -> Collection:
    """初始化或加载向量存储"""
    connect_to_milvus()

    if not utility.has_collection(collection_name):
        raise ValueError(
            f"Collection {collection_name} does not exist. Please create it first."
        )

    collection = Collection(collection_name)

    # 加载集合
    collection.load()
    return collection


def get_entity_retriever(collection: Collection, entity_type: str) -> Callable:
    """获取实体检索器"""

    def retriever(query: str, k: int = 1) -> List[Dict]:
        embedding_model = CustomEmbeddings(
            api_key=os.getenv("EMBEDDING_API_KEY", ""),
            api_url=os.getenv("EMBEDDING_API_BASE", ""),
            model=os.getenv("EMBEDDING_MODEL", ""),
        )
        query_embedding = embedding_model.embed_query(query)

        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        # 获取集合的字段信息
        field_names = [field.name for field in collection.schema.fields]

        # 确定原始名称字段和标准名称字段
        original_name_field = (
            "company_name" if "company_name" in field_names else "school_name"
        )
        standard_name_field = (
            "standard_name" if "standard_name" in field_names else original_name_field
        )

        # 设置输出字段
        output_fields = [original_name_field, standard_name_field]

        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=output_fields,
        )

        retrieved_entities = []
        for hits in results:
            for hit in hits:
                entity = {
                    "original_name": hit.entity.get(original_name_field),
                    "standard_name": hit.entity.get(standard_name_field),
                    "distance": hit.distance,
                }
                retrieved_entities.append(entity)

        return retrieved_entities

    return retriever
