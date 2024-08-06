import streamlit as st
from PIL import Image
import pandas as pd
import plotly.graph_objects as go
import sys
import os
import numpy as np
import io
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import hashlib

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.shared_components import show_sidebar, show_footer, apply_common_styles
from backend.data_processing.analysis.feature_importance_evaluator import (
    encode_categorical_variables,
    random_forest_analysis,
    shap_analysis,
    linear_regression_analysis,
    filter_dataframe,
    calculate_shap_dependence,
)

# Streamlit 页面配置
st.set_page_config(
    page_title="智能HR助手 - 影响因素分析",
    page_icon="📊",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


# 初始化会话状态
def initialize_session_state():
    """
    初始化 Streamlit 会话状态，设置默认值。
    """
    default_states = {
        "param_ranges": {
            "n_estimators": (10, 100),
            "max_depth": (5, 20),
            "min_samples_split": (2, 20),
            "min_samples_leaf": (1, 20),
            "max_features": ["sqrt", "log2"],
        },
        "best_params": None,
        "df": None,
        "filtered_df": None,
        "selected_columns": None,
        "filters": [],
        "model": None,
        "feature_importance": None,
        "shap_values": None,
        "model_hash": None,
    }

    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session_state()


def calculate_model_hash(
    analysis_method, use_optuna, param_ranges, target_column, feature_columns, filters
):
    """
    计算模型的哈希值，用于确定是否需要重新训练模型。

    Args:
        analysis_method (str): 分析方法。
        use_optuna (bool): 是否使用 Optuna 进行参数优化。
        param_ranges (dict): 参数范围。
        target_column (str): 目标列名。
        feature_columns (list): 特征列名列表。
        filters (list): 应用的过滤器列表。

    Returns:
        str: 计算得到的哈希值。
    """
    hash_string = f"{analysis_method}_{use_optuna}_{param_ranges}_{target_column}_{feature_columns}_{filters}"
    return hashlib.md5(hash_string.encode()).hexdigest()


def plot_impact(impact, title):
    """
    绘制影响因素的条形图。

    Args:
        impact (pd.Series): 包含影响度数据的 Series。
        title (str): 图表标题。
    """
    impact_sorted = impact.sort_values(ascending=True)
    fig = go.Figure(
        data=[go.Bar(x=impact_sorted.values, y=impact_sorted.index, orientation="h")]
    )
    fig.update_layout(
        title=title,
        xaxis_title="影响度",
        yaxis_title="因素",
        height=max(500, len(impact_sorted) * 20),
        width=800,
        margin=dict(l=200),
    )
    st.plotly_chart(fig)


def create_excel_download(corr_matrix, feature_importance, shap_values=None):
    """
    创建包含分析结果的 Excel 文件。

    Args:
        corr_matrix (pd.DataFrame): 相关性矩阵。
        feature_importance (pd.DataFrame): 特征重要性数据。
        shap_values (pd.DataFrame, optional): SHAP 值数据。

    Returns:
        bytes: Excel 文件的二进制数据。
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        corr_matrix.to_excel(writer, sheet_name="相关性热图")
        feature_importance.reset_index().to_excel(
            writer, sheet_name="特征重要性", index=False
        )
        if shap_values is not None:
            shap_values.reset_index().to_excel(writer, sheet_name="SHAP值", index=False)
    output.seek(0)
    return output


