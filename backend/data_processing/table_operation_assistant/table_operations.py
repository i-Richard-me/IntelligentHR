import pandas as pd
from langchain_core.tools import tool
from typing import Annotated, List, Dict, Union, Any, Optional, Tuple

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@tool
def merge_dataframes(
    left_df: Annotated[Any, "左侧数据表，包含要合并的数据"],
    right_df: Annotated[Any, "右侧数据表，将与左侧数据表合并"],
    how: Annotated[
        str,
        "合并方式: 'inner'（内连接）, 'outer'（外连接）, 'left'（左连接）, 或 'right'（右连接）",
    ],
    left_on: Annotated[
        Union[str, List[str]], "左侧数据表用于合并的列名或列名列表，这些列将作为连接键"
    ],
    right_on: Annotated[
        Union[str, List[str]], "右侧数据表用于合并的列名或列名列表，这些列将作为连接键"
    ],
    left_columns: Annotated[
        Optional[List[str]],
        "要包含在结果中的左侧数据表列名列表，如果为None则包含所有列",
    ] = None,
    right_columns: Annotated[
        Optional[List[str]],
        "要包含在结果中的右侧数据表列名列表，如果为None则包含所有列",
    ] = None,
) -> pd.DataFrame:
    """
    合并两个数据表，基于指定的列进行连接操作。这个函数允许灵活地选择连接方式和要包含的列。

    使用场景：
    - 当需要基于共同信息（如ID或日期）组合两个相关的数据集时。
    - 在需要将多个数据源的信息整合到一个统一视图中时。

    注意：
    - 确保用于连接的列在两个数据表中都存在。
    - 选择适当的连接方式（how参数）以避免意外的数据丢失。
    - 对于left_columns和right_columns参数：
      * 如果用户没有明确指定或说明，默认会包含所有列。
    """
    try:
        # 选择要包含的列
        if left_columns is not None:
            left_df = left_df[left_columns]
        if right_columns is not None:
            right_df = right_df[right_columns]

        # 确保合并键包含在选定的列中
        if isinstance(left_on, str):
            left_on = [left_on]
        if isinstance(right_on, str):
            right_on = [right_on]

        left_df = left_df[list(set(left_df.columns) | set(left_on))]
        right_df = right_df[list(set(right_df.columns) | set(right_on))]

        # 执行合并
        merged_df = pd.merge(
            left_df, right_df, how=how, left_on=left_on, right_on=right_on
        )
        logger.info(f"Merged dataframes successfully. Result shape: {merged_df.shape}")

        return merged_df
    except Exception as e:
        logger.error(f"Error in merge_dataframes: {str(e)}")
        raise


@tool
def reshape_wide_to_long(
    df: Annotated[
        Any,
        "输入的宽格式数据表，其中每行代表一个唯一实体，多个时间点或类别的数据分布在不同列中",
    ],
    columns_to_compress: Annotated[
        List[str], "需要被压缩成长格式的列名列表，这些列将被转换为单个列中的值"
    ],
    new_column_for_old_headers: Annotated[
        str, "新的列名，用于存储原来的列名（作为标识符）"
    ],
    new_column_for_values: Annotated[str, "新的列名，用于存储原来列的值"],
) -> pd.DataFrame:
    """
    将宽格式的数据表重塑（reshape）为长格式。这个过程通常被称为"melting"或"unpivoting"。

    使用场景：
    - 当数据以宽格式存储，但分析或可视化需要长格式时。
    - 准备数据用于时间序列分析或纵向数据分析。
    - 将多列数据合并为单一的类别列和值列，便于特定类型的统计分析。

    注意：
    - 确保 columns_to_compress 中列出的所有列确实存在于数据表中。
    - 对于new_column_for_old_headers和new_column_for_values参数：
      * 如果用户没有明确指定这些新列的名称，你可以根据数据的上下文自动生成合适的名称。
    """
    try:
        # 自动确定需要保留的列
        columns_to_keep = [col for col in df.columns if col not in columns_to_compress]

        # 执行宽转长操作
        long_df = pd.melt(
            df,
            id_vars=columns_to_keep,
            value_vars=columns_to_compress,
            var_name=new_column_for_old_headers,
            value_name=new_column_for_values,
        )

        # 重置索引
        long_df = long_df.reset_index(drop=True)
        logger.info(
            f"Reshaped dataframe from wide to long format. New shape: {long_df.shape}"
        )

        return long_df
    except Exception as e:
        logger.error(f"Error in reshape_wide_to_long: {str(e)}")
        raise


@tool
def reshape_long_to_wide(
    df: Annotated[
        Any, "输入的长格式数据表，其中一列包含将成为新列名的值，另一列包含这些新列的值"
    ],
    column_to_use_as_headers: Annotated[str, "包含将成为新列名的值的列名"],
    column_with_values: Annotated[str, "包含将成为新列值的列名"],
    aggfunc: Annotated[
        str, "当有重复值时使用的聚合函数，如'first', 'last', 'mean', 'sum'等"
    ] = "first",
) -> pd.DataFrame:
    """
    将长格式的数据表重塑（reshape）为宽格式。这个过程通常被称为"pivoting"或"casting"。

    使用场景：
    - 将长格式的时间序列数据转换为每个时间点一列的格式。
    - 创建交叉表或透视表，用于数据汇总和报告。
    - 准备数据用于特定类型的统计分析或可视化，这些分析或可视化要求宽格式数据。

    注意：
    - 确保 column_to_use_as_headers 和 column_with_values 列确实存在于数据表中。
    """
    try:
        # 自动确定标识列
        id_columns = [
            col
            for col in df.columns
            if col not in [column_to_use_as_headers, column_with_values]
        ]

        # 执行长转宽操作
        wide_df = df.pivot_table(
            index=id_columns,
            columns=column_to_use_as_headers,
            values=column_with_values,
            aggfunc=aggfunc,
        )

        # 重置列名，移除 MultiIndex
        wide_df.columns.name = None
        wide_df = wide_df.reset_index()
        logger.info(
            f"Reshaped dataframe from long to wide format. New shape: {wide_df.shape}"
        )

        return wide_df
    except Exception as e:
        logger.error(f"Error in reshape_long_to_wide: {str(e)}")
        raise


@tool
def compare_dataframes(
    df1: Annotated[Any, "第一个数据表，作为比较的基准"],
    df2: Annotated[Any, "第二个数据表，用于与第一个数据表进行比较"],
    key_column_df1: Annotated[str, "df1中用于比较的关键列名，用于标识唯一记录"],
    key_column_df2: Annotated[
        Union[str, None], "df2中用于比较的关键列名，如果与df1相同，可以不指定"
    ] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    比较两个数据表，基于指定的关键列，找出它们之间的差异。

    使用场景：
    - 检查数据更新后的变化，如找出新增或删除的记录。
    - 验证数据迁移或转换的完整性。
    - 对比两个相似但可能有差异的数据集，如不同时间点的快照。
    """
    try:
        # 如果没有指定df2的关键列名，则使用与df1相同的列名
        if key_column_df2 is None:
            key_column_df2 = key_column_df1

        # 确保两个数据表都有指定的关键列
        if key_column_df1 not in df1.columns:
            raise ValueError(f"关键列 '{key_column_df1}' 不存在于第一个数据表中")
        if key_column_df2 not in df2.columns:
            raise ValueError(f"关键列 '{key_column_df2}' 不存在于第二个数据表中")

        # 获取两个数据表中关键列的唯一值集合
        set_df1 = set(df1[key_column_df1])
        set_df2 = set(df2[key_column_df2])

        # 找出只在df1中存在的记录
        only_in_df1 = df1[df1[key_column_df1].isin(set_df1 - set_df2)].reset_index(
            drop=True
        )

        # 找出只在df2中存在的记录
        only_in_df2 = df2[df2[key_column_df2].isin(set_df2 - set_df1)].reset_index(
            drop=True
        )

        logger.info(
            f"Comparison complete. Records only in df1: {len(only_in_df1)}, only in df2: {len(only_in_df2)}"
        )

        return only_in_df1, only_in_df2
    except Exception as e:
        logger.error(f"Error in compare_dataframes: {str(e)}")
        raise
