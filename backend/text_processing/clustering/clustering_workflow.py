import uuid
from typing import List, Dict, Any, Optional
import pandas as pd
from langfuse.callback import CallbackHandler
from utils.llm_tools import LanguageModelChain, init_language_model
from utils.text_utils import (
    clean_text_columns,
    filter_invalid_text,
    dataframe_to_markdown_tables,
)
from backend.text_processing.clustering.clustering_core import (
    Categories,
    ClassificationResult,
    INITIAL_CATEGORY_GENERATION_SYSTEM_MESSAGE,
    INITIAL_CATEGORY_GENERATION_HUMAN_MESSAGE,
    MERGE_CATEGORIES_SYSTEM_MESSAGE,
    MERGE_CATEGORIES_HUMAN_MESSAGE,
    TEXT_CLASSIFICATION_SYSTEM_MESSAGE,
    TEXT_CLASSIFICATION_HUMAN_MESSAGE,
)

# 初始化语言模型
language_model = init_language_model()


def create_langfuse_handler(session_id: str, step: str) -> CallbackHandler:
    """
    创建Langfuse回调处理器

    Args:
        session_id: 会话ID
        step: 当前步骤名称

    Returns:
        CallbackHandler: Langfuse回调处理器实例
    """
    return CallbackHandler(
        tags=["text_clustering"], session_id=session_id, metadata={"step": step}
    )


def generate_unique_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    为DataFrame生成唯一ID，格式为'ID'后跟6位数字

    Args:
        df: 输入的DataFrame

    Returns:
        pd.DataFrame: 添加了唯一ID列的DataFrame
    """
    df["unique_id"] = [f"ID{i:06d}" for i in range(1, len(df) + 1)]
    return df


def preprocess_data(df: pd.DataFrame, text_column: str) -> pd.DataFrame:
    """
    预处理数据：清洗文本列，过滤无效文本，生成唯一ID

    Args:
        df: 输入的DataFrame
        text_column: 包含文本数据的列名

    Returns:
        pd.DataFrame: 预处理后的DataFrame
    """
    df = clean_text_columns(df)
    df = filter_invalid_text(df, text_column)
    df = generate_unique_ids(df)
    return df


def batch_texts(df: pd.DataFrame, text_column: str, batch_size: int = 100) -> List[str]:
    """
    将文本数据分批处理

    Args:
        df: 包含文本数据的DataFrame
        text_column: 文本列的名称
        batch_size: 每批处理的文本数量

    Returns:
        List[str]: 批处理后的文本列表
    """
    return [
        " ".join(df[text_column].iloc[i : i + batch_size].tolist())
        for i in range(0, len(df), batch_size)
    ]


def generate_initial_categories(
    texts: List[str], text_topic: str, category_count: int, session_id: str
) -> List[Dict]:
    """
    生成初始类别

    Args:
        texts: 待分类的文本列表
        text_topic: 文本主题或背景
        category_count: 期望生成的类别数量
        session_id: 会话ID

    Returns:
        List[Dict]: 生成的初始类别列表
    """
    langfuse_handler = create_langfuse_handler(session_id, "initial_categories")
    category_chain = LanguageModelChain(
        Categories,
        INITIAL_CATEGORY_GENERATION_SYSTEM_MESSAGE,
        INITIAL_CATEGORY_GENERATION_HUMAN_MESSAGE,
        language_model,
    )()

    categories_list = []
    for text_batch in texts:
        result = category_chain.invoke(
            {
                "text_topic": text_topic,
                "text_content": text_batch,
                "category_count": category_count,
            },
            config={"callbacks": [langfuse_handler]},
        )
        categories_list.append(result)

    return categories_list


def merge_categories(
    categories_list: List[Dict],
    text_topic: str,
    min_categories: int,
    max_categories: int,
    session_id: str,
) -> Dict:
    """
    合并生成的类别

    Args:
        categories_list: 初始类别列表
        text_topic: 文本主题或背景
        min_categories: 最小类别数量
        max_categories: 最大类别数量
        session_id: 会话ID

    Returns:
        Dict: 合并后的类别字典
    """
    langfuse_handler = create_langfuse_handler(session_id, "merge_categories")
    merge_chain = LanguageModelChain(
        Categories,
        MERGE_CATEGORIES_SYSTEM_MESSAGE,
        MERGE_CATEGORIES_HUMAN_MESSAGE,
        language_model,
    )()

    result = merge_chain.invoke(
        {
            "text_topic": text_topic,
            "classification_results": categories_list,
            "min_categories": min_categories,
            "max_categories": max_categories,
        },
        config={"callbacks": [langfuse_handler]},
    )

    return result


def generate_categories(
    df: pd.DataFrame,
    text_column: str,
    text_topic: str,
    initial_category_count: int,
    min_categories: int,
    max_categories: int,
    batch_size: int = 100,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成类别的主函数

    Args:
        df: 输入的DataFrame
        text_column: 文本列的名称
        text_topic: 文本主题或背景
        initial_category_count: 初始类别数量
        min_categories: 最小类别数量
        max_categories: 最大类别数量
        batch_size: 批处理大小
        session_id: 会话ID（可选）

    Returns:
        Dict[str, Any]: 包含生成的类别、预处理后的DataFrame和会话ID的字典
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    preprocessed_df = preprocess_data(df, text_column)
    batched_texts = batch_texts(preprocessed_df, text_column, batch_size)
    initial_categories = generate_initial_categories(
        batched_texts, text_topic, initial_category_count, session_id
    )
    merged_categories = merge_categories(
        initial_categories, text_topic, min_categories, max_categories, session_id
    )

    return {
        "categories": merged_categories,
        "preprocessed_df": preprocessed_df,
        "session_id": session_id,
    }


def classify_texts(
    df: pd.DataFrame,
    text_column: str,
    id_column: str,
    categories: Dict,
    text_topic: str,
    session_id: str,
    classification_batch_size: int = 20,
) -> pd.DataFrame:
    """
    对文本进行分类

    Args:
        df: 包含文本数据的DataFrame
        text_column: 文本列的名称
        id_column: ID列的名称
        categories: 类别字典
        text_topic: 文本主题或背景
        session_id: 会话ID
        classification_batch_size: 分类批处理大小

    Returns:
        pd.DataFrame: 包含分类结果的DataFrame
    """
    langfuse_handler = create_langfuse_handler(session_id, "classify_texts")

    classification_chain = LanguageModelChain(
        ClassificationResult,
        TEXT_CLASSIFICATION_SYSTEM_MESSAGE,
        TEXT_CLASSIFICATION_HUMAN_MESSAGE,
        language_model,
    )()

    markdown_tables = dataframe_to_markdown_tables(
        df, [id_column, text_column], rows_per_table=classification_batch_size
    )

    classification_results = []
    for table in markdown_tables:
        result = classification_chain.invoke(
            {"text_topic": text_topic, "categories": categories, "text_table": table},
            config={"callbacks": [langfuse_handler]},
        )
        classification_results.extend(result["classifications"])

    df_classifications = pd.DataFrame(classification_results)
    df_result = df.merge(
        df_classifications, left_on="unique_id", right_on="id", how="left"
    )
    df_result = df_result.drop(columns=["unique_id", "id"])

    return df_result
