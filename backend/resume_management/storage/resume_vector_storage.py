"""
简历向量存储模块

本模块负责简历数据的向量存储操作，使用 Milvus 向量数据库进行存储和检索。
"""

import os
import json
from typing import Dict, Any, List, Union

import pandas as pd
from pymilvus import connections, Collection

from utils.llm_tools import VectorEncoder
from utils.vector_db_utils import (
    connect_to_milvus,
    create_milvus_collection,
    initialize_vector_store,
    insert_to_milvus,
    update_milvus_records,
)

# 初始化 embedding 服务
embeddings = VectorEncoder(model="BAAI/bge-m3")

# 加载集合配置
COLLECTIONS_CONFIG_PATH = "data/config/collections_config.json"
with open(COLLECTIONS_CONFIG_PATH, "r", encoding="utf-8") as f:
    COLLECTIONS_CONFIG = json.load(f)["collections"]


def get_embedding(text: Union[str, List[str]]) -> List[float]:
    """
    获取文本的嵌入向量

    Args:
        text (Union[str, List[str]]): 输入文本或文本列表

    Returns:
        List[float]: 文本的嵌入向量
    """
    if isinstance(text, list):
        text = " ".join(text)
    if not text or text.strip() == "":
        return [0] * 1024  # 返回 1024 维的零向量
    return embeddings.get_embedding(text)


def prepare_data_for_milvus(
    data: Dict[str, Any], collection_name: str, resume_id: str
) -> tuple:
    """
    准备用于 Milvus 存储的数据

    Args:
        data (Dict[str, Any]): 原始数据
        collection_name (str): 集合名称
        resume_id (str): 简历 ID

    Returns:
        tuple: 处理后的数据记录和向量
    """
    config = COLLECTIONS_CONFIG[collection_name]
    df = pd.DataFrame(data if isinstance(data, list) else [data])
    df["resume_id"] = resume_id

    # 处理列表类型的字段和长文本
    for column in df.columns:
        if df[column].dtype == "object":
            df[column] = df[column].apply(lambda x: process_field(x, column))

    vectors = {
        field: df[field].apply(get_embedding).tolist()
        for field in config["embedding_fields"]
        if field in df.columns
    }

    return df.to_dict("records"), vectors


def process_field(value: Any, field_name: str) -> str:
    """
    处理字段值，转换列表和转义特殊字符

    Args:
        value (Any): 字段值
        field_name (str): 字段名称

    Returns:
        str: 处理后的字段值
    """
    if isinstance(value, list):
        value = " ".join(map(str, value))
    if isinstance(value, str):
        value = value.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
    return str(value)


def store_resume_in_milvus(resume_data: Dict[str, Any]):
    """
    将解析后的简历数据存储到 Milvus 中

    Args:
        resume_data (Dict[str, Any]): 解析后的简历数据
    """
    connect_to_milvus(db_name=os.getenv("VECTOR_DB_DATABASE_RESUME", "resume"))

    try:
        resume_id = resume_data["id"]
        for collection_name in [
            "personal_infos",
            "educations",
            "work_experiences",
            "project_experiences",
            "skills",
        ]:
            config = COLLECTIONS_CONFIG[collection_name]

            # 初始化或创建集合
            try:
                collection = initialize_vector_store(collection_name)
            except ValueError:
                collection = create_milvus_collection(config, dim=1024)

            # 准备数据
            data = None
            if collection_name == "personal_infos":
                data = resume_data["personal_info"]
            elif collection_name == "educations":
                data = resume_data["education"]
            elif collection_name == "work_experiences":
                data = resume_data["work_experiences"]
            elif collection_name == "project_experiences" and resume_data.get(
                "project_experiences"
            ):
                data = resume_data["project_experiences"]
            elif collection_name == "skills" and resume_data["personal_info"].get(
                "skills"
            ):
                data = [
                    {"skill": skill} for skill in resume_data["personal_info"]["skills"]
                ]

            if data:
                records, vectors = prepare_data_for_milvus(
                    data, collection_name, resume_id
                )
                update_milvus_records(
                    collection, records, vectors, config["embedding_fields"]
                )

    except Exception as e:
        raise Exception(f"存储简历数据时出错: {str(e)}")
    finally:
        connections.disconnect("default")
