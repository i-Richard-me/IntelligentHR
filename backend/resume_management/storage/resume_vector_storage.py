import os
import json
from pymilvus import connections, Collection, DataType
from typing import Dict, Any, List, Union
import pandas as pd
from utils.llm_tools import VectorEncoder
from utils.vector_db_utils import (
    connect_to_milvus,
    create_milvus_collection,
    initialize_vector_store,
    insert_to_milvus,
    update_milvus_records,
)
import re

# 初始化embedding服务
embeddings = VectorEncoder(model="BAAI/bge-m3")

# 加载集合配置
with open("data/config/collections_config.json", "r") as f:
    collections_config = json.load(f)["collections"]


def get_embedding(text: Union[str, List[str]]) -> List[float]:
    """获取文本的嵌入向量"""
    if isinstance(text, list):
        text = " ".join(text)
    if not text or text.strip() == "":
        return [0] * 1024  # 返回1024维的零向量
    return embeddings.get_embedding(text)


def prepare_data_for_milvus(
    data: Dict[str, Any], collection_name: str, resume_id: str
) -> tuple:
    config = collections_config[collection_name]
    df = pd.DataFrame(data if isinstance(data, list) else [data])
    df["resume_id"] = resume_id

    # 将列表类型的字段转换为字符串，并处理长文本
    for column in df.columns:
        if df[column].dtype == "object":
            df[column] = df[column].apply(lambda x: process_field(x, column))

    vectors = {}
    for field in config["embedding_fields"]:
        if field in df.columns:
            vectors[field] = df[field].apply(get_embedding).tolist()

    return df.to_dict("records"), vectors


def escape_quotes(text):
    # 首先替换反斜杠，然后是双引号，最后是单引号
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")


def process_field(value, field_name):
    if isinstance(value, list):
        value = " ".join(value)
    if isinstance(value, str):
        # 移除可能导致问题的特殊字符
        value = escape_quotes(value)
    return value


def store_resume_in_milvus(resume_data: Dict[str, Any]):
    """将解析后的简历数据存储到Milvus中"""
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
            config = collections_config[collection_name]

            # 检查集合是否存在，如果不存在则创建
            try:
                collection = initialize_vector_store(collection_name)
            except ValueError:
                collection = create_milvus_collection(config, dim=1024)

            if collection_name == "personal_infos":
                personal_info = resume_data["personal_info"]
                personal_info["characteristics"] = resume_data.get(
                    "characteristics", ""
                )
                personal_info["experience_summary"] = resume_data.get(
                    "experience_summary", ""
                )
                personal_info["skills_overview"] = resume_data.get(
                    "skills_overview", ""
                )
                data, vectors = prepare_data_for_milvus(
                    personal_info, collection_name, resume_id
                )
            elif collection_name == "educations":
                data, vectors = prepare_data_for_milvus(
                    resume_data["education"], collection_name, resume_id
                )
            elif collection_name == "work_experiences":
                data, vectors = prepare_data_for_milvus(
                    resume_data["work_experiences"], collection_name, resume_id
                )
            elif collection_name == "project_experiences" and resume_data.get(
                "project_experiences"
            ):
                data, vectors = prepare_data_for_milvus(
                    resume_data["project_experiences"], collection_name, resume_id
                )
            elif collection_name == "skills" and resume_data["personal_info"].get(
                "skills"
            ):
                skills_data = [
                    {"skill": skill} for skill in resume_data["personal_info"]["skills"]
                ]
                data, vectors = prepare_data_for_milvus(
                    skills_data, collection_name, resume_id
                )
            else:
                continue

            update_milvus_records(collection, data, vectors, config["embedding_fields"])
    except Exception as e:
        raise Exception(f"存储简历数据时出错: {str(e)}")
    finally:
        connections.disconnect("default")
