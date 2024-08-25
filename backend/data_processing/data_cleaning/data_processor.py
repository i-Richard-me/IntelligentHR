import os
from typing import List, Dict, Callable
import pandas as pd
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)

from utils.llm_tools import CustomEmbeddings

# Milvus 连接配置
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_DB = "examples"


def connect_to_milvus():
    """连接到 Milvus 数据库"""
    connections.connect(
        alias="default", host=MILVUS_HOST, port=MILVUS_PORT, db_name=MILVUS_DB
    )


def create_milvus_collection(collection_name: str, dim: int):
    """创建 Milvus 集合"""
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="company_name", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="school_name", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="standard_name", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]

    schema = CollectionSchema(fields, f"Collection for {collection_name}")
    collection = Collection(collection_name, schema)
    return collection


def initialize_vector_store(collection_name: str) -> Collection:
    """初始化或加载向量存储"""
    connect_to_milvus()

    if not utility.has_collection(collection_name):
        # 假设嵌入维度为 1536（根据您使用的嵌入模型可能需要调整）
        collection = create_milvus_collection(collection_name, dim=1536)
    else:
        collection = Collection(collection_name)

    # 创建索引（如果尚未创建）
    if not collection.has_index():
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024},
        }
        collection.create_index("embedding", index_params)

    collection.load()
    return collection


def get_entity_retriever(collection: Collection, entity_type: str) -> Callable:
    """获取实体检索器"""

    def retriever(query: str, k: int = 1) -> List[Dict]:
        embedding_model = CustomEmbeddings(os.getenv("OPENAI_API_KEY_SILICONCLOUD"))
        query_embedding = embedding_model.embed_query(query)

        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        original_field = "company_name" if entity_type == "公司名称" else "school_name"
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=[original_field, "standard_name"],
        )

        retrieved_entities = []
        for hits in results:
            for hit in hits:
                entity = {
                    "original_name": hit.entity.get(original_field),
                    "standard_name": hit.entity.get("standard_name"),
                    "distance": hit.distance,
                }
                retrieved_entities.append(entity)

        return retrieved_entities

    return retriever


def load_entity_data(file_path: str) -> pd.DataFrame:
    """从 CSV 文件加载实体数据"""
    return pd.read_csv(file_path)
