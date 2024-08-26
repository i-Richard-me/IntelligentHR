import os
from pymilvus import connections, Collection, DataType
from typing import Dict, Any, List
import pandas as pd
from utils.llm_tools import VectorEncoder

# 初始化embedding服务
embeddings = VectorEncoder(model="BAAI/bge-m3")


def connect_to_milvus(
    host: str = os.getenv("VECTOR_DB_HOST", "localhost"),
    port: str = os.getenv("VECTOR_DB_PORT", "19530"),
    db_name: str = os.getenv("VECTOR_DB_DATABASE_RESUME", "resume"),
):
    """连接到Milvus数据库"""
    connections.connect(host=host, port=port, db_name=db_name)
    print(f"Connected to Milvus database: {db_name}")


def disconnect_from_milvus():
    """断开与Milvus数据库的连接"""
    connections.disconnect("default")
    print("Disconnected from Milvus database")


def get_embedding(text: str) -> List[float]:
    """获取文本的嵌入向量"""
    if not text or text.strip() == "":
        return [0] * 1024  # 返回1024维的零向量
    return embeddings.get_embedding(text)


def prepare_data_for_milvus(
    data: Dict[str, Any], collection_name: str, resume_id: str
) -> pd.DataFrame:
    if collection_name == "personal_infos":
        df = pd.DataFrame([data])
        df["summary_vector"] = df["summary"].apply(get_embedding)
    elif collection_name == "educations":
        df = pd.DataFrame(data)
        df["degree_vector"] = df["degree"].apply(get_embedding)
        df["major_vector"] = df["major"].apply(get_embedding)
    elif collection_name == "work_experiences":
        df = pd.DataFrame(data)
        df["position_vector"] = df["position"].apply(get_embedding)
        df["responsibilities_text"] = df["responsibilities"].apply(
            lambda x: " ".join(x) if isinstance(x, list) else x
        )
        df["responsibilities_vector"] = df["responsibilities_text"].apply(get_embedding)
    elif collection_name == "project_experiences":
        df = pd.DataFrame(data)
        df["name_vector"] = df["name"].apply(get_embedding)
        df["details_text"] = df["details"].apply(
            lambda x: " ".join(x) if isinstance(x, list) else x
        )
        df["details_vector"] = df["details_text"].apply(get_embedding)
    elif collection_name == "skills":
        df = pd.DataFrame(data)
        df["skill_vector"] = df["skill"].apply(get_embedding)
    else:
        raise ValueError(f"Unknown collection name: {collection_name}")

    # 确保所有 DataFrame 都包含 resume_id
    if "resume_id" not in df.columns:
        df["resume_id"] = resume_id

    return df


def insert_data_to_milvus(collection_name: str, data: Dict[str, Any], resume_id: str):
    """将数据插入到Milvus集合中"""
    collection = Collection(collection_name)
    schema = collection.schema

    df = prepare_data_for_milvus(data, collection_name, resume_id)

    # 获取schema中定义的所有字段名称、类型和长度限制
    schema_fields = {
        field.name: (field.dtype, field.params.get("max_length"))
        for field in schema.fields
    }

    # 只保留dataframe中在schema中定义的列
    valid_fields = list(set(schema_fields.keys()).intersection(set(df.columns)))
    filtered_df = df[valid_fields].copy()

    # 转换数据类型并截断过长的字符串
    for field, (dtype, max_length) in schema_fields.items():
        if field in filtered_df.columns:
            if dtype == DataType.VARCHAR:
                filtered_df[field] = filtered_df[field].astype(str)
                if max_length:
                    filtered_df[field] = filtered_df[field].apply(
                        lambda x: x[:max_length] if x else x
                    )
            elif dtype in [DataType.INT64, DataType.INT32]:
                filtered_df[field] = pd.to_numeric(
                    filtered_df[field], errors="coerce"
                ).astype("Int64")

    # 准备数据
    insert_data = filtered_df.to_dict("records")

    # 插入数据
    try:
        collection.insert(insert_data)
        print(
            f"Successfully inserted {len(insert_data)} records into {collection_name}"
        )
    except Exception as e:
        print(f"Error inserting data into {collection_name}: {e}")

    # 刷新collection以确保数据可见
    collection.flush()


def store_resume_in_milvus(resume_data: Dict[str, Any]):
    """将解析后的简历数据存储到Milvus中"""
    connect_to_milvus()

    try:
        resume_id = resume_data["id"]
        insert_data_to_milvus("personal_infos", resume_data["personal_info"], resume_id)
        insert_data_to_milvus("educations", resume_data["education"], resume_id)
        insert_data_to_milvus(
            "work_experiences", resume_data["work_experiences"], resume_id
        )
        if "project_experiences" in resume_data and resume_data["project_experiences"]:
            insert_data_to_milvus(
                "project_experiences", resume_data["project_experiences"], resume_id
            )
        if (
            "skills" in resume_data["personal_info"]
            and resume_data["personal_info"]["skills"]
        ):
            skills_data = [
                {"resume_id": resume_id, "skill": skill}
                for skill in resume_data["personal_info"]["skills"]
            ]
            insert_data_to_milvus("skills", skills_data, resume_id)
    finally:
        disconnect_from_milvus()
