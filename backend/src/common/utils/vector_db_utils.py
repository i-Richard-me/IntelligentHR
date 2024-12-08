import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)

logger = logging.getLogger(__name__)


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
                "metric_type": "IP",
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
    search_params = {"metric_type": "IP", "params": {"nprobe": 10}}

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
    search_params = {"metric_type": "IP", "params": {"nprobe": 10}}

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


async def async_connect_to_milvus(db_name: str = "default"):
    """
    异步连接到 Milvus 数据库。

    Args:
        db_name (str): 要连接的数据库名称。默认为 "default"。
    """
    await asyncio.to_thread(
        connections.connect,
        alias="default",
        host=os.getenv("VECTOR_DB_HOST", "localhost"),
        port=os.getenv("VECTOR_DB_PORT", "19530"),
        db_name=db_name,
    )


async def async_initialize_vector_store(collection_name: str) -> Collection:
    """
    异步初始化或加载向量存储。

    Args:
        collection_name (str): 集合名称。

    Returns:
        Collection: Milvus 集合对象。

    Raises:
        ValueError: 如果集合不存在。
    """
    has_collection = await asyncio.to_thread(utility.has_collection, collection_name)
    if not has_collection:
        raise ValueError(
            f"Collection {collection_name} does not exist. Please create it first."
        )

    collection = Collection(collection_name)
    await asyncio.to_thread(collection.load)
    return collection


async def async_create_milvus_collection(collection_config: Dict[str, Any], dim: int) -> Collection:
    """
    异步创建 Milvus 集合，支持多个向量字段。

    Args:
        collection_config (Dict[str, Any]): 集合配置。
        dim (int): 向量维度。

    Returns:
        Collection: 创建的 Milvus 集合对象。
    """
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    ]
    
    # 添加字段
    for field in collection_config["fields"]:
        fields.append(
            FieldSchema(name=field["name"], dtype=DataType.VARCHAR, max_length=65535)
        )
        if field.get("is_vector", False):
            fields.append(
                FieldSchema(
                    name=f"{field['name']}_vector",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=dim
                )
            )

    schema = CollectionSchema(fields, collection_config["description"])
    
    # 建集合
    collection = await asyncio.to_thread(
        Collection, collection_config["name"], schema
    )

    # 为向量字段创建索引
    for field in collection.schema.fields:
        if field.name.endswith("_vector"):
            index_params = {
                "metric_type": "IP",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
            }
            await asyncio.to_thread(
                collection.create_index,
                field.name,
                index_params
            )

    await asyncio.to_thread(collection.load)
    return collection


async def async_insert_to_milvus(
    collection: Collection,
    data: List[Dict[str, Any]],
    vectors: Dict[str, List[List[float]]],
):
    """
    异步将数据插入 Milvus 集合。

    Args:
        collection (Collection): Milvus 集合对象。
        data (List[Dict[str, Any]]): 要插入的数据。
        vectors (Dict[str, List[List[float]]]): 对应的向量数据。
    """
    entities = []
    for field in collection.schema.fields:
        if field.name not in ["id"] and not field.name.endswith("_vector"):
            entities.append([d.get(field.name) for d in data])
        elif field.name.endswith("_vector"):
            original_field_name = field.name[:-7]
            entities.append(vectors.get(original_field_name, []))

    await asyncio.to_thread(collection.insert, entities)
    await asyncio.to_thread(collection.load)


async def async_update_milvus_records(
    collection: Collection,
    data: List[Dict[str, Any]],
    vectors: Dict[str, List[List[float]]],
    embedding_fields: List[str],
):
    """
    异步更新 Milvus 集合中的记录。

    Args:
        collection (Collection): Milvus 集合对象。
        data (List[Dict[str, Any]]): 要更新的数据。
        vectors (Dict[str, List[List[float]]]): 对应的向量数据。
        embedding_fields (List[str]): 用于生成向量的字段名列表。
    """
    for record in data:
        # 构建查询表达式
        query_expr = " && ".join(
            [f"{field} == '{record[field]}'" for field in embedding_fields]
        )
        
        # 查询现有记录
        existing_records = await asyncio.to_thread(
            collection.query,
            expr=query_expr,
            output_fields=["id"],
        )

        if existing_records:
            # 删除现有记录
            await asyncio.to_thread(
                collection.delete,
                expr=f"id in {[r['id'] for r in existing_records]}"
            )

        # 准备新记录
        entities = []
        for field in collection.schema.fields:
            if field.name not in ["id"] and not field.name.endswith("_vector"):
                entities.append([record.get(field.name)])
            elif field.name.endswith("_vector"):
                original_field_name = field.name[:-7]
                entities.append([vectors[original_field_name][data.index(record)]])

        # 插入新记录
        await asyncio.to_thread(collection.insert, entities)

    await asyncio.to_thread(collection.load)


async def async_delete_from_milvus(
    collection: Collection,
    expr: str,
) -> int:
    """
    异步从 Milvus 集合中删除记录。

    Args:
        collection (Collection): Milvus 集合对象。
        expr (str): 删除条件表达式。

    Returns:
        int: 删除的记录数量。
    """
    result = await asyncio.to_thread(collection.delete, expr)
    await asyncio.to_thread(collection.load)
    return result.delete_count


async def async_search_in_milvus(
    collection: Collection,
    query_vector: List[float],
    vector_field: str,
    top_k: int = 1,
    expr: Optional[str] = None,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """异步在 Milvus 集合中搜索最相似的向量。

    Args:
        collection (Collection): Milvus 集合对象。
        query_vector (List[float]): 查询向量。
        vector_field (str): 要搜索的向量字段名。
        top_k (int): 返回的最相似结果数量。
        expr (str, optional): 额外的过滤条件。
        offset (int): 分页偏移量。

    Returns:
        List[Dict[str, Any]]: 搜索结果列表。
    """
    search_params = {"metric_type": "IP", "params": {"nprobe": 10}}

    output_fields = [
        field.name
        for field in collection.schema.fields
        if not field.name.endswith("_vector")
    ]

    results = await asyncio.to_thread(
        collection.search,
        data=[query_vector],
        anns_field=f"{vector_field}_vector",
        param=search_params,
        limit=top_k,
        expr=expr,
        output_fields=output_fields,
        offset=offset
    )

    return [
        {
            "id": str(hit.id),  # Convert ID to string
            **{field: getattr(hit.entity, field) for field in output_fields if field != "id"},
            "distance": hit.distance,
        }
        for hit in results[0]
    ]


async def async_get_actual_count(collection: Collection) -> int:
    """
    异步获取集合中的实际记录数（不包括已删除的记录）。
    
    Args:
        collection (Collection): Milvus 集合对象。
        
    Returns:
        int: 实际记录数。
    """
    try:
        # 使用 count 操作获取实际记录数
        result = await asyncio.to_thread(
            collection.query,
            expr="id >= 0",  # 一个始终为真的条件
            output_fields=["count(*)"],
            consistency_level="Strong"  # 使用强一致性以获取最新结果
        )
        return result[0]["count(*)"] if result else 0
    except Exception as e:
        logger.error(f"Failed to get actual count: {str(e)}")
        # 如果查询失败，回退到使用 num_entities
        return collection.num_entities


async def async_get_collection_stats(collection: Collection) -> Dict[str, Any]:
    """
    异步获取集合的统计信息。

    Args:
        collection (Collection): Milvus 集合对象。

    Returns:
        Dict[str, Any]: 包含集合统计信息的字典。
    """
    actual_count = await async_get_actual_count(collection)
    index_info = await asyncio.to_thread(lambda: collection.index().params)
    
    stats = {
        "实体数量": actual_count,
        "字段数量": len(collection.schema.fields) - 1,  # 减去自动生成的 id 字段
        "索引类型": index_info.get("index_type", "未知"),
    }
    return stats


async def async_list_collections(db_name: str = "default") -> List[str]:
    """
    异步获取数据库中的所有集合名称。

    Args:
        db_name (str): 数据库名称。

    Returns:
        List[str]: 集合名称列表。
    """
    await async_connect_to_milvus(db_name)
    return await asyncio.to_thread(utility.list_collections)


async def async_get_collection_loading_progress(collection: Collection) -> float:
    """
    异步获取集合加载进度。

    Args:
        collection (Collection): Milvus 集合对象。

    Returns:
        float: 加载进度（0-1之间的数值）。
    """
    progress = await asyncio.to_thread(collection.loading_progress)
    return progress


async def async_drop_collection(collection_name: str) -> None:
    """
    异步删除集���。

    Args:
        collection_name (str): 要删除的集合名称。
    """
    if await asyncio.to_thread(utility.has_collection, collection_name):
        await asyncio.to_thread(utility.drop_collection, collection_name)