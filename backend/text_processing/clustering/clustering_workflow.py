from typing import List, Dict, Any
import pandas as pd
from utils.llm_tools import LanguageModelChain, init_language_model
from utils.text_utils import (
    clean_text_columns,
    filter_invalid_text,
    dataframe_to_markdown_tables,
)
from backend.text_processing.clustering.clustering_core import (
    Categories,
    ClassificationResult,
)
from backend.text_processing.clustering.clustering_core import (
    INITIAL_CATEGORY_GENERATION_SYSTEM_MESSAGE,
    INITIAL_CATEGORY_GENERATION_HUMAN_MESSAGE,
    MERGE_CATEGORIES_SYSTEM_MESSAGE,
    MERGE_CATEGORIES_HUMAN_MESSAGE,
    TEXT_CLASSIFICATION_SYSTEM_MESSAGE,
    TEXT_CLASSIFICATION_HUMAN_MESSAGE,
)

# 初始化语言模型
language_model = init_language_model()


def generate_unique_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    为DataFrame生成唯一ID，格式为'ID'后跟6位数字

    Args:
        df (pd.DataFrame): 输入的数据框

    Returns:
        pd.DataFrame: 添加了唯一ID列的数据框
    """
    num_rows = len(df)
    df["unique_id"] = [f"ID{i:06d}" for i in range(1, num_rows + 1)]
    return df


def preprocess_data(df: pd.DataFrame, text_column: str) -> pd.DataFrame:
    """
    对输入的数据框进行预处理

    Args:
        df (pd.DataFrame): 输入的数据框
        text_column (str): 包含文本数据的列名

    Returns:
        pd.DataFrame: 预处理后的数据框
    """
    df = clean_text_columns(df)
    df = filter_invalid_text(df, text_column)
    df = generate_unique_ids(df)
    return df


def batch_texts(df: pd.DataFrame, text_column: str, batch_size: int = 100) -> List[str]:
    """
    将文本数据分批处理

    Args:
        df (pd.DataFrame): 包含文本数据的数据框
        text_column (str): 文本列的名称
        batch_size (int, optional): 每批处理的文本数量，默认为100

    Returns:
        List[str]: 分批后的文本列表
    """
    return [
        " ".join(df[text_column].iloc[i : i + batch_size].tolist())
        for i in range(0, len(df), batch_size)
    ]


def generate_initial_categories(
    texts: List[str], text_topic: str, category_count: int
) -> List[Dict]:
    """
    为给定的文本生成初始类别

    Args:
        texts (List[str]): 待分类的文本列表
        text_topic (str): 文本主题
        category_count (int): 需要生成的类别数量

    Returns:
        List[Dict]: 生成的初始类别列表
    """
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
            }
        )
        categories_list.append(result)

    return categories_list


def merge_categories(
    categories_list: List[Dict],
    text_topic: str,
    min_categories: int,
    max_categories: int,
) -> Dict:
    """
    合并并优化生成的类别

    Args:
        categories_list (List[Dict]): 初始类别列表
        text_topic (str): 文本主题
        min_categories (int): 最小类别数量
        max_categories (int): 最大类别数量

    Returns:
        Dict: 合并后的类别字典
    """
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
        }
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
) -> Dict[str, Any]:
    """
    生成文本类别的主函数

    Args:
        df (pd.DataFrame): 包含文本数据的数据框
        text_column (str): 文本列的名称
        text_topic (str): 文本主题
        initial_category_count (int): 初始类别数量
        min_categories (int): 最小类别数量
        max_categories (int): 最大类别数量
        batch_size (int, optional): 每批处理的文本数量，默认为100

    Returns:
        Dict[str, Any]: 包含生成的类别和预处理后的数据框的字典
    """
    # 预处理数据
    preprocessed_df = preprocess_data(df, text_column)

    # 将文本分批
    batched_texts = batch_texts(preprocessed_df, text_column, batch_size)

    # 生成初始类别
    initial_categories = generate_initial_categories(
        batched_texts, text_topic, initial_category_count
    )

    # 合并类别
    merged_categories = merge_categories(
        initial_categories, text_topic, min_categories, max_categories
    )

    return {"categories": merged_categories, "preprocessed_df": preprocessed_df}


def classify_texts(
    df: pd.DataFrame,
    text_column: str,
    id_column: str,
    categories: Dict,
    text_topic: str,
) -> pd.DataFrame:
    """
    对文本进行分类

    Args:
        df (pd.DataFrame): 包含文本数据的数据框
        text_column (str): 文本列的名称
        id_column (str): ID列的名称
        categories (Dict): 分类类别字典
        text_topic (str): 文本主题

    Returns:
        pd.DataFrame: 包含分类结果的数据框
    """
    classification_chain = LanguageModelChain(
        ClassificationResult,
        TEXT_CLASSIFICATION_SYSTEM_MESSAGE,
        TEXT_CLASSIFICATION_HUMAN_MESSAGE,
        language_model,
    )()

    markdown_tables = dataframe_to_markdown_tables(df, [id_column, text_column])

    classification_results = []
    for table in markdown_tables:
        result = classification_chain.invoke(
            {"text_topic": text_topic, "categories": categories, "text_table": table}
        )
        classification_results.extend(result["classifications"])

    # 创建分类结果的DataFrame
    df_classifications = pd.DataFrame(classification_results)

    # 将分类结果合并到原始DataFrame
    df_result = df.merge(
        df_classifications, left_on="unique_id", right_on="id", how="left"
    )

    # 移除中间处理字段
    df_result = df_result.drop(columns=["unique_id", "id"])

    return df_result


def cluster_texts(
    df: pd.DataFrame,
    text_column: str,
    text_topic: str,
    initial_category_count: int,
    min_categories: int,
    max_categories: int,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """
    执行文本聚类的主函数

    Args:
        df (pd.DataFrame): 包含文本数据的数据框
        text_column (str): 文本列的名称
        text_topic (str): 文本主题
        initial_category_count (int): 初始类别数量
        min_categories (int): 最小类别数量
        max_categories (int): 最大类别数量
        batch_size (int, optional): 每批处理的文本数量，默认为100

    Returns:
        Dict[str, Any]: 包含聚类类别和分类结果的字典
    """
    # 预处理数据
    preprocessed_df = preprocess_data(df, text_column)

    # 生成类别
    category_result = generate_categories(
        preprocessed_df,
        text_column,
        text_topic,
        initial_category_count,
        min_categories,
        max_categories,
        batch_size,
    )
    merged_categories = category_result["categories"]

    # 对所有文本进行分类
    classified_df = classify_texts(
        preprocessed_df, text_column, "unique_id", merged_categories, text_topic
    )

    return {"categories": merged_categories, "classifications": classified_df}
