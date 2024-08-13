import os
from typing import List, Dict, Tuple

import pandas as pd
from langchain_core.documents import Document
from langchain_milvus import Milvus

from utils.llm_tools import CustomEmbeddings


def load_company_data(file_path: str) -> pd.DataFrame:
    """
    从CSV文件加载公司数据。

    Args:
        file_path (str): CSV文件的路径。

    Returns:
        pd.DataFrame: 包含公司数据的DataFrame。
    """
    return pd.read_csv(file_path)


def create_company_documents(company_data: pd.DataFrame) -> List[Document]:
    """
    从公司数据创建文档列表。

    Args:
        company_data (pd.DataFrame): 包含公司数据的DataFrame。

    Returns:
        List[Document]: 公司文档列表。
    """
    return [
        Document(
            page_content=str(row.iloc[0]),
            metadata={
                "company_abbreviation": str(row.iloc[1]),
            },
        )
        for _, row in company_data.iterrows()
    ]


def initialize_vector_store(
    use_demo: bool, collection_name: str = "company_data"
) -> Milvus:
    """
    初始化或加载向量存储。

    Args:
        use_demo (bool): 是否使用演示数据。
        collection_name (str): Milvus集合名称。

    Returns:
        Milvus: 初始化的Milvus向量存储。
    """
    embedding_model = CustomEmbeddings(os.getenv("OPENAI_API_KEY_SILICONCLOUD"))

    connection_args = {"host": "localhost", "port": "19530", "db_name": "data_cleaning"}

    if use_demo:
        csv_path = "data/company.csv"
        company_data = load_company_data(csv_path)
        documents = create_company_documents(company_data)
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


def get_company_retriever(vector_store: Milvus, k: int = 1):
    """
    获取公司检索器。

    Args:
        vector_store (Milvus): Milvus向量存储。
        k (int): 检索的最近邻数量。

    Returns:
        Retriever: 公司检索器。
    """
    return vector_store.as_retriever(search_kwargs={"k": k})
