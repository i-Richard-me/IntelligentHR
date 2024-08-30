import os
from typing import List, Dict, Any
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)


def connect_to_milvus(db_name: str = "default"):
    """
    连接到 Milvus 数据库。

    Args:
        db_name (str): 要连接的数据库名称。默认为 "default"。
    """
    connections.connect(
        alias="default",
        host=os.getenv("VECTOR_DB_HOST", "localhost"),
        port=os.getenv("VECTOR_DB_PORT", "19530"),
        db_name=db_name,
    )


def initialize_vector_store(collection_name: str) -> Collection:
    """
    初始化或加载向量存储。

    Args:
        collection_name (str): 集合名称。

    Returns:
        Collection: Milvus 集合对象。

    Raises:
        ValueError: 如果集合不存在。
    """
    if not utility.has_collection(collection_name):
        raise ValueError(
            f"Collection {collection_name} does not exist. Please create it first."
        )

    collection = Collection(collection_name)
    collection.load()
    return collection


def create_milvus_collection(collection_config: Dict[str, Any], dim: int) -> Collection:
    """
    创建 Milvus 集合。

    Args:
        collection_config (Dict[str, Any]): 集合配置。
        dim (int): 向量维度。

    Returns:
        Collection: 创建的 Milvus 集合对象。
    """
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    ]
    for field in collection_config["fields"]:
        fields.append(
            FieldSchema(name=field["name"], dtype=DataType.VARCHAR, max_length=65535)
        )
    fields.append(FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim))

    schema = CollectionSchema(fields, collection_config["description"])
    collection = Collection(collection_config["name"], schema)
    return collection


def insert_to_milvus(
    collection: Collection, data: List[Dict[str, Any]], vectors: List[List[float]]
):
    """
    将数据插入 Milvus 集合。

    Args:
        collection (Collection): Milvus 集合对象。
        data (List[Dict[str, Any]]): 要插入的数据。
        vectors (List[List[float]]): 对应的向量数据。
    """
    entities = [list(d.values()) for d in data]
    entities.append(vectors)
    collection.insert(entities)

    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024},
    }
    collection.create_index("embedding", index_params)
    collection.load()


def search_in_milvus(
    collection: Collection, query_vector: List[float], top_k: int = 1
) -> List[Dict[str, Any]]:
    """
    在 Milvus 集合中搜索最相似的向量。

    Args:
        collection (Collection): Milvus 集合对象。
        query_vector (List[float]): 查询向量。
        top_k (int): 返回的最相似结果数量。默认为1。

    Returns:
        List[Dict[str, Any]]: 搜索结果列表。
    """
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

    # 获取所有字段名称，排除 'id' 和 'embedding' 字段
    output_fields = [
        field.name
        for field in collection.schema.fields
        if field.name not in ["id", "embedding"]
    ]

    results = collection.search(
        data=[query_vector],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=output_fields,
    )

    return [
        {
            **{field: getattr(hit.entity, field) for field in output_fields},
            "distance": hit.distance,
        }
        for hit in results[0]
    ]


def get_collection_stats(collection: Collection) -> Dict[str, Any]:
    """
    获取集合的统计信息。

    Args:
        collection (Collection): Milvus 集合对象。

    Returns:
        Dict[str, Any]: 包含集合统计信息的字典。
    """
    stats = {
        "实体数量": collection.num_entities,
        "字段数量": len(collection.schema.fields) - 1,  # 减去自动生成的 id 字段
        "索引类型": collection.index().params.get("index_type", "未知"),
    }
    return stats
