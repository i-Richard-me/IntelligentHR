import os
import asyncio
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
    创建 Milvus 集合，支持多个向量字段，并为向量字段创建索引。

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
        if field.get("is_vector", False):
            fields.append(
                FieldSchema(
                    name=f"{field['name']}_vector", dtype=DataType.FLOAT_VECTOR, dim=dim
                )
            )

    schema = CollectionSchema(fields, collection_config["description"])
    collection = Collection(collection_config["name"], schema)

    # 为向量字段创建索引
    for field in collection.schema.fields:
        if field.name.endswith("_vector"):
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
            }
            collection.create_index(field.name, index_params)

    collection.load()
    return collection


def insert_to_milvus(
    collection: Collection,
    data: List[Dict[str, Any]],
    vectors: Dict[str, List[List[float]]],
):
    """
    将数据插入 Milvus 集合，支持多个向量字段。

    Args:
        collection (Collection): Milvus 集合对象。
        data (List[Dict[str, Any]]): 要插入的数据，每个字典代表一行数据。
        vectors (Dict[str, List[List[float]]]): 对应的向量数据，键为字段名，值为向量列表。
    """
    entities = []
    for field in collection.schema.fields:
        if field.name not in ["id"] and not field.name.endswith("_vector"):
            entities.append([d.get(field.name) for d in data])
        elif field.name.endswith("_vector"):
            original_field_name = field.name[:-7]  # 去掉 "_vector" 后缀
            entities.append(vectors.get(original_field_name, []))

    collection.insert(entities)
    collection.load()


def update_milvus_records(
    collection: Collection,
    data: List[Dict[str, Any]],
    vectors: Dict[str, List[List[float]]],
    embedding_fields: List[str],
):
    """
    更新 Milvus 集合中的记录，支持多个向量字段。如果记录不存在，则插入新记录。

    Args:
        collection (Collection): Milvus 集合对象。
        data (List[Dict[str, Any]]): 要更新的数据，每个字典代表一行数据。
        vectors (Dict[str, List[List[float]]]): 对应的向量数据，键为字段名，值为向量列表。
        embedding_fields (List[str]): 用于生成向量的字段名列表。
    """
    for record in data:
        # 使用所有 embedding_fields 构建查询表达式
        query_expr = " && ".join(
            [f"{field} == '{record[field]}'" for field in embedding_fields]
        )
        existing_records = collection.query(
            expr=query_expr,
            output_fields=["id"],
        )

        if existing_records:
            # 更新现有记录
            collection.delete(expr=f"id in {[r['id'] for r in existing_records]}")

        # 插入记录（无论是新记录还是更新后的记录）
        entities = []
        for field in collection.schema.fields:
            if field.name not in ["id"] and not field.name.endswith("_vector"):
                entities.append([record.get(field.name)])
            elif field.name.endswith("_vector"):
                original_field_name = field.name[:-7]  # 去掉 "_vector" 后缀
                entities.append([vectors[original_field_name][data.index(record)]])

        collection.insert(entities)

    collection.load()


def search_in_milvus(
    collection: Collection, query_vector: List[float], vector_field: str, top_k: int = 1
) -> List[Dict[str, Any]]:
    """
    在 Milvus 集合中搜索最相似的向量。

    Args:
        collection (Collection): Milvus 集合对象。
        query_vector (List[float]): 查询向量。
        vector_field (str): 要搜索的向量字段名。
        top_k (int): 返回的最相似结果数量。默认为1。

    Returns:
        List[Dict[str, Any]]: 搜索结果列表。
    """
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

    output_fields = [
        field.name
        for field in collection.schema.fields
        if not field.name.endswith("_vector") and field.name != "id"
    ]

    results = collection.search(
        data=[query_vector],
        anns_field=f"{vector_field}_vector",
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


async def asearch_in_milvus(
    collection: Collection, query_vector: List[float], vector_field: str, top_k: int = 1
) -> List[Dict[str, Any]]:
    """
    在 Milvus 集合中异步搜索最相似的向量。

    Args:
        collection (Collection): Milvus 集合对象。
        query_vector (List[float]): 查询向量。
        vector_field (str): 要搜索的向量字段名。
        top_k (int): 返回的最相似结果数量。默认为1。

    Returns:
        List[Dict[str, Any]]: 搜索结果列表。
    """
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

    output_fields = [
        field.name
        for field in collection.schema.fields
        if not field.name.endswith("_vector") and field.name != "id"
    ]

    # 使用 asyncio.to_thread 来在线程中运行同步操作
    results = await asyncio.to_thread(
        collection.search,
        data=[query_vector],
        anns_field=f"{vector_field}_vector",
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
