import os
from typing import List, Dict, Tuple

import pandas as pd
from langchain_core.documents import Document
from langchain_milvus import Milvus

from utils.llm_tools import CustomEmbeddings


def load_entity_data(file_path: str) -> pd.DataFrame:
    """
    从CSV文件加载实体数据。

    Args:
        file_path (str): CSV文件的路径。

    Returns:
        pd.DataFrame: 包含实体数据的DataFrame。
    """
    return pd.read_csv(file_path)


def create_entity_documents(
    entity_data: pd.DataFrame, entity_type: str
) -> List[Document]:
    """
    从实体数据创建文档列表。

    Args:
        entity_data (pd.DataFrame): 包含实体数据的DataFrame。
        entity_type (str): 实体类型（如 "company" 或 "school"）。

    Returns:
        List[Document]: 实体文档列表。
    """
    name_column = f"{entity_type}_name"
    return [
        Document(
            page_content=str(row[name_column]),
            metadata={
                "standard_name": str(row["standard_name"]),
            },
        )
        for _, row in entity_data.iterrows()
    ]


def initialize_vector_store(
    use_demo: bool, entity_type: str, collection_name: str
) -> Milvus:
    """
    初始化或加载向量存储。

    Args:
        use_demo (bool): 是否使用演示数据。
        entity_type (str): 实体类型（如 "company" 或 "school"）。
        collection_name (str): Milvus集合名称。

    Returns:
        Milvus: 初始化的Milvus向量存储。
    """
    embedding_model = CustomEmbeddings(os.getenv("OPENAI_API_KEY_SILICONCLOUD"))

    connection_args = {"host": "localhost", "port": "19530", "db_name": "data_cleaning"}

    if use_demo:
        csv_path = f"data/datasets/{entity_type}.csv"
        entity_data = load_entity_data(csv_path)
        documents = create_entity_documents(entity_data, entity_type)
        return Milvus.from_documents(
            documents=documents,
            embedding=embedding_model,
            collection_name=collection_name,
            connection_args=connection_args,
            drop_old=True,
        )
    else:
        return Milvus(
            embedding_function=embedding_model,
            collection_name=collection_name,
            connection_args=connection_args,
        )


def get_entity_retriever(vector_store: Milvus, k: int = 1):
    """
    获取实体检索器。

    Args:
        vector_store (Milvus): Milvus向量存储。
        k (int): 检索的最近邻数量。

    Returns:
        Retriever: 实体检索器。
    """
    return vector_store.as_retriever(search_kwargs={"k": k})
