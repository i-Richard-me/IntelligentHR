import random
from typing import List, Literal, Union, Optional
import pandas as pd
import regex as re

def check_language_type(df: pd.DataFrame, text_col: str) -> pd.DataFrame:
    """
    检查数据集中指定文本字段的内容是否为中文，并添加一个标记列。

    Args:
        df (pd.DataFrame): 包含文本字段的数据集
        text_col (str): 需要检查的文本字段名称

    Returns:
        pd.DataFrame: 返回原数据集，增加一个标记列 'is_chinese'，表示文本是否为中文

    Raises:
        ValueError: 如果输入不是pandas DataFrame或指定的列不存在
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError("输入必须是pandas DataFrame类型")
    if text_col not in df.columns:
        raise ValueError(f"指定的列 '{text_col}' 在DataFrame中不存在")

    def contains_chinese(text):
        if isinstance(text, str):
            chinese_chars = re.findall("[\u4e00-\u9fff]", text)
            return len(chinese_chars) / len(text) >= 0.5 if text else False
        return False

    df["is_chinese"] = df[text_col].apply(contains_chinese)
    return df