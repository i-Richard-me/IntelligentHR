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

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
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


def main():
    """
    主函数，包含影响因素分析的整个流程。
    """
    st.title("📊 影响因素分析")
    st.markdown("---")

    display_info_message()
    display_workflow()

    uploaded_file = upload_file()
    if uploaded_file is None:
        return

    display_data_filtering()
    display_column_selection_and_preprocessing()
    display_correlation_heatmap()
    display_model_analysis()
    display_feature_importance()
    display_shap_analysis()
    display_download_button()

    show_footer()


def display_info_message():
    """
    显示影响因素分析工具的信息消息。
    """
    st.info(
        """
    **🔍 影响因素分析工具**

    影响因素分析功能结合统计和机器学习方法，帮助用户识别和量化各种因素对特定目标变量的影响程度。
    
    核心分析包括多种模型（如线性回归和随机森林）、SHAP值分析和依赖图。通过交互式可视化，
    可以直观地探索和解释分析结果。
    
    该工具还支持模型参数优化，并提供数据筛选和异常值处理等辅助功能，
    适用于各种需要深入理解变量关系和影响因素的数据分析场景。
    """
    )


def display_workflow():
    """
    显示影响因素分析的工作流程。
    """
    with st.expander("📋 查看影响因素分析工作流程", expanded=False):
        st.markdown(
            '<h2 class="section-title">影响因素分析工作流程</h2>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            col1, col2 = st.columns([1, 1])

            with col1:
                image = Image.open(
                    "frontend/assets/feature_importance_evaluator_workflow.png"
                )
                st.image(image, caption="影响因素分析流程图", use_column_width=True)

            with col2:
                st.markdown(
                    """
                    **1. 数据准备**
                    选择目标变量和相关特征，对数据进行必要的筛选和预处理。
                    
                    **2. 初步分析**
                    生成相关性热图，直观展示变量间的关联强度。
        
                    **3. 模型训练**
                    训练线性回归或随机森林模型，可选择使用参数自动调优来优化性能。
        
                    **4. 特征重要性**
                    计算模型的特征重要性，并进行SHAP值分析以量化特征贡献。
        
                    **5. 模型解释**
                    通过SHAP依赖图和特征交互分析，深入解释模型预测和特征影响。
        
                    **6. 结果可视化**
                    使用重要性排序图和交互式SHAP图表，直观呈现分析结果。
                """
                )


def upload_file():
    """
    处理文件上传并加载数据。

    Returns:
        pd.DataFrame or None: 加载的数据框，如果上传失败则返回None。
    """
    st.markdown('<h2 class="section-title">数据上传</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "上传CSV或Excel文件", type=["csv", "xlsx", "xls"]
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    st.session_state.df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith((".xls", ".xlsx")):
                    st.session_state.df = pd.read_excel(uploaded_file)
                else:
                    st.error("不支持的文件格式。请上传CSV或Excel文件。")
                    return None

                st.success("文件上传成功！")
                st.write(
                    f"数据集包含 {len(st.session_state.df)} 行和 {len(st.session_state.df.columns)} 列"
                )
                st.write(st.session_state.df.head())
                return st.session_state.df

            except Exception as e:
                st.error(f"处理文件时出错：{str(e)}")
                return None

    return None


def display_data_filtering():
    """
    显示并处理数据筛选界面。
    """
    if st.session_state.df is None:
        return

    st.markdown('<h2 class="section-title">数据筛选</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        add_filter()
        display_current_filters()
        apply_filters()


def add_filter():
    """
    添加新的筛选条件。
    """
    col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
    with col1:
        filter_column = st.selectbox(
            "选择筛选字段",
            [""] + list(st.session_state.df.columns),
            key="filter_column",
        )

    if filter_column:
        with col2:
            filter_type = get_filter_type(filter_column)
        with col3:
            filter_value = get_filter_value(filter_column, filter_type)
        with col4:
            if st.button("添加", key="add_filter"):
                st.session_state.filters.append(
                    (filter_column, filter_type, filter_value)
                )
                apply_filter(filter_column, filter_type, filter_value)
                st.rerun()


def get_filter_type(column):
    """
    根据列的数据类型获取适当的筛选类型。

    Args:
        column (str): 列名。

    Returns:
        str: 筛选类型。
    """
    if st.session_state.df[column].dtype == "object":
        return st.selectbox(
            "筛选类型", ["包含", "不包含", "为空", "非空"], key="filter_type"
        )
    else:
        return st.selectbox(
            "筛选类型",
            [
                "大于",
                "大于等于",
                "小于",
                "小于等于",
                "等于",
                "不等于",
                "之间",
                "为空",
                "非空",
            ],
            key="filter_type",
        )


def get_filter_value(column, filter_type):
    """
    根据列和筛选类型获取筛选值。

    Args:
        column (str): 列名。
        filter_type (str): 筛选类型。

    Returns:
        任意: 筛选值。
    """
    if st.session_state.df[column].dtype == "object":
        if filter_type in ["包含", "不包含"]:
            return st.multiselect(
                "选择值", st.session_state.df[column].unique(), key="filter_value"
            )
        else:  # "为空" 或 "非空"
            return None
    elif filter_type == "之间":
        return st.slider(
            "选择范围",
            float(st.session_state.df[column].min()),
            float(st.session_state.df[column].max()),
            (
                float(st.session_state.df[column].min()),
                float(st.session_state.df[column].max()),
            ),
            key="filter_value",
        )
    elif filter_type in ["为空", "非空"]:
        return None
    else:
        return st.number_input(
            "输入值",
            value=float(st.session_state.df[column].mean()),
            key="filter_value",
        )


def display_current_filters():
    """
    显示当前的筛选条件。
    """
    if st.session_state.filters:
        with st.expander("当前筛选条件", expanded=True):
            for i, (col, type_, val) in enumerate(st.session_state.filters):
                col1, col2 = st.columns([5, 1])
                with col1:
                    if val is None:
                        st.write(f"{i + 1}. {col} {type_}")
                    else:
                        st.write(f"{i + 1}. {col} {type_} {val}")
                with col2:
                    if st.button("删除", key=f"delete_{i}"):
                        st.session_state.filters.pop(i)
                        apply_filters()
                        st.rerun()


def apply_filters():
    """
    应用所有筛选条件到数据框。
    """
    if st.button("清除所有筛选条件"):
        st.session_state.filters = []
        st.session_state.filtered_df = st.session_state.df
        reset_selected_columns()
        st.rerun()

    if st.session_state.filters:
        filters = {col: (type_, val) for col, type_, val in st.session_state.filters}
        st.session_state.filtered_df = filter_dataframe(st.session_state.df, filters)
        st.write(f"筛选后的数据集包含 {len(st.session_state.filtered_df)} 行")
        st.write(st.session_state.filtered_df.head())
    else:
        st.session_state.filtered_df = st.session_state.df


def apply_filter(column, filter_type, filter_value):
    """
    应用单个筛选条件到数据框。

    Args:
        column (str): 列名。
        filter_type (str): 筛选类型。
        filter_value: 筛选值。
    """
    filters = {column: (filter_type, filter_value)}
    st.session_state.filtered_df = filter_dataframe(
        st.session_state.filtered_df, filters
    )
    update_selected_columns()


def reset_selected_columns():
    """
    重置选中的列为所有数值列。
    """
    numeric_columns = st.session_state.df.select_dtypes(
        include=[np.number]
    ).columns.tolist()
    st.session_state.selected_columns = numeric_columns


def update_selected_columns():
    """
    更新选中的列，移除筛选后不存在的列。
    """
    if (
        "selected_columns" in st.session_state
        and st.session_state.selected_columns is not None
    ):
        st.session_state.selected_columns = [
            col
            for col in st.session_state.selected_columns
            if col in st.session_state.filtered_df.columns
        ]
    else:
        reset_selected_columns()


def display_column_selection_and_preprocessing():
    """
    显示列选择和预处理选项。
    """
    if st.session_state.filtered_df is None:
        return

    st.markdown(
        '<h2 class="section-title">选择分析列和预处理</h2>', unsafe_allow_html=True
    )
    with st.container(border=True):
        handle_categorical_encoding()
        select_analysis_columns()


def handle_categorical_encoding():
    """
    处理分类变量的编码。
    """
    categorical_columns = st.session_state.filtered_df.select_dtypes(
        include=["object"]
    ).columns.tolist()
    if categorical_columns:
        encode_categorical = st.checkbox("对离散变量进行编码")
        if encode_categorical:
            selected_categorical = st.multiselect(
                "选择要编码的离散变量", categorical_columns
            )
            if selected_categorical:
                st.session_state.filtered_df = encode_categorical_variables(
                    st.session_state.filtered_df, selected_categorical
                )
                st.success("离散变量编码完成！")


def select_analysis_columns():
    """
    选择要分析的列。
    """
    numeric_columns = st.session_state.filtered_df.select_dtypes(
        include=[np.number]
    ).columns.tolist()
    columns_without_none = [
        col
        for col in numeric_columns
        if not st.session_state.filtered_df[col].isnull().any()
    ]

    if (
        "selected_columns" not in st.session_state
        or st.session_state.selected_columns is None
    ):
        st.session_state.selected_columns = columns_without_none
    else:
        st.session_state.selected_columns = [
            col
            for col in st.session_state.selected_columns
            if col in columns_without_none
        ]

    selected_columns = st.multiselect(
        "选择要分析的列", numeric_columns, default=st.session_state.selected_columns
    )

    handle_columns_with_none(selected_columns)

    st.session_state.selected_columns = selected_columns

    if len(st.session_state.selected_columns) < 2:
        st.warning("请至少选择两列进行分析。")


def handle_columns_with_none(selected_columns):
    """
    处理包含None值的列。

    Args:
        selected_columns (list): 选中的列名列表。
    """
    columns_with_none = [
        col
        for col in selected_columns
        if st.session_state.filtered_df[col].isnull().any()
    ]

    if columns_with_none:
        rows_before = len(st.session_state.filtered_df)
        st.session_state.filtered_df = st.session_state.filtered_df.dropna(
            subset=selected_columns
        )
        rows_after = len(st.session_state.filtered_df)

        st.warning(
            f"以下选择的字段包含None值：{', '.join(columns_with_none)}\n\n"
            f"已删除包含None值的{rows_before - rows_after}行数据。"
        )


def display_correlation_heatmap():
    """
    显示相关性热图。
    """
    if st.session_state.filtered_df is None or not st.session_state.selected_columns:
        return

    st.markdown('<h2 class="section-title">相关性热图</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        corr_matrix = st.session_state.filtered_df[
            st.session_state.selected_columns
        ].corr()
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        corr_matrix_low = corr_matrix.mask(mask)

        fig = go.Figure(
            data=go.Heatmap(
                z=corr_matrix_low.values,
                x=corr_matrix_low.columns,
                y=corr_matrix_low.index,
                colorscale="RdBu",
                zmin=-1,
                zmax=1,
            )
        )
        fig.update_layout(height=600, width=800)
        st.plotly_chart(fig)


def display_model_analysis():
    """
    显示模型分析选项并执行分析。
    """
    if st.session_state.filtered_df is None or not st.session_state.selected_columns:
        return

    st.markdown('<h2 class="section-title">模型分析与解释</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        target_column = st.selectbox("选择目标列", st.session_state.selected_columns)
        feature_columns = [
            col for col in st.session_state.selected_columns if col != target_column
        ]

        analysis_method = st.radio("选择分析方法", ["线性回归", "随机森林"])
        use_shap = st.checkbox("使用SHAP值解释模型")
        st.session_state.use_shap = use_shap

        X = st.session_state.filtered_df[feature_columns]
        y = st.session_state.filtered_df[target_column]

        use_optuna = False
        if analysis_method == "随机森林":
            use_optuna = st.checkbox("使用 Optuna 优化随机森林参数")
            if use_optuna:
                display_advanced_settings()

        perform_model_analysis(
            analysis_method, use_optuna, X, y, target_column, feature_columns
        )


def display_advanced_settings():
    """
    显示高级设置选项。
    """
    with st.expander("高级设置"):
        st.write("自定义参数搜索范围")
        n_estimators_range = st.slider(
            "n_estimators 范围", 5, 300, st.session_state.param_ranges["n_estimators"]
        )
        max_depth_range = st.slider(
            "max_depth 范围", 1, 100, st.session_state.param_ranges["max_depth"]
        )
        min_samples_split_range = st.slider(
            "min_samples_split 范围",
            2,
            50,
            st.session_state.param_ranges["min_samples_split"],
        )
        min_samples_leaf_range = st.slider(
            "min_samples_leaf 范围",
            1,
            50,
            st.session_state.param_ranges["min_samples_leaf"],
        )
        max_features_options = st.multiselect(
            "max_features 选项",
            ["sqrt", "log2", "auto"],
            default=st.session_state.param_ranges["max_features"],
        )

        if st.button("确认参数设置"):
            update_param_ranges(
                n_estimators_range,
                max_depth_range,
                min_samples_split_range,
                min_samples_leaf_range,
                max_features_options,
            )


def update_param_ranges(
    n_estimators, max_depth, min_samples_split, min_samples_leaf, max_features
):
    """
    更新参数范围设置。

    Args:
        n_estimators (tuple): n_estimators 的范围。
        max_depth (tuple): max_depth 的范围。
        min_samples_split (tuple): min_samples_split 的范围。
        min_samples_leaf (tuple): min_samples_leaf 的范围。
        max_features (list): max_features 的选项列表。
    """
    st.session_state.param_ranges["n_estimators"] = n_estimators
    st.session_state.param_ranges["max_depth"] = max_depth
    st.session_state.param_ranges["min_samples_split"] = min_samples_split
    st.session_state.param_ranges["min_samples_leaf"] = min_samples_leaf
    st.session_state.param_ranges["max_features"] = max_features
    st.success("参数设置已更新")


def perform_model_analysis(
    analysis_method, use_optuna, X, y, target_column, feature_columns
):
    """
    执行模型分析。

    Args:
        analysis_method (str): 分析方法（"线性回归"或"随机森林"）。
        use_optuna (bool): 是否使用Optuna优化参数。
        X (pd.DataFrame): 特征数据。
        y (pd.Series): 目标变量。
        target_column (str): 目标列名。
        feature_columns (list): 特征列名列表。
    """
    new_model_hash = calculate_model_hash(
        analysis_method,
        use_optuna,
        st.session_state.param_ranges,
        target_column,
        feature_columns,
        st.session_state.filters,
    )

    if new_model_hash != st.session_state.model_hash:
        st.session_state.model = None
        st.session_state.feature_importance = None
        st.session_state.shap_values = None
        st.session_state.model_hash = new_model_hash

    if st.session_state.model is None:
        with st.spinner("正在训练模型..."):
            if analysis_method == "线性回归":
                st.session_state.model, st.session_state.feature_importance = (
                    linear_regression_analysis(X, y)
                )
            else:  # 随机森林
                (
                    st.session_state.model,
                    st.session_state.feature_importance,
                    best_params,
                ) = random_forest_analysis(
                    X, y, use_optuna, st.session_state.param_ranges
                )
                if use_optuna and best_params:
                    with st.expander("查看随机森林最佳参数"):
                        st.json(best_params)
        st.success("模型训练完成！")


def display_feature_importance():
    """
    显示特征重要性图表。
    """
    if st.session_state.feature_importance is None:
        return

    st.markdown('<h2 class="section-title">模型特征重要性</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        plot_impact(
            st.session_state.feature_importance,
            f"各因素对 {st.session_state.selected_columns[0]} 的影响度",
        )


def display_shap_analysis():
    """
    显示SHAP值分析结果。
    """
    if not st.session_state.get("use_shap", False) or st.session_state.model is None:
        return

    st.markdown('<h2 class="section-title">SHAP值分析</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        if st.session_state.shap_values is None:
            with st.spinner("正在计算SHAP值..."):
                X = st.session_state.filtered_df[st.session_state.selected_columns[1:]]
                st.session_state.shap_values = shap_analysis(st.session_state.model, X)

        if st.session_state.shap_values is not None:
            plot_impact(
                st.session_state.shap_values,
                f"各因素对 {st.session_state.selected_columns[0]} 的SHAP值",
            )
            display_shap_dependence()
        else:
            st.error("无法计算SHAP值。请确保模型和数据已正确加载。")


def display_shap_dependence():
    """
    显示SHAP依赖图。
    """
    show_shap_dependence = st.checkbox("展示SHAP依赖图")
    if show_shap_dependence:
        st.markdown('<h3 class="section-title">SHAP依赖图</h3>', unsafe_allow_html=True)

        plot_all = st.checkbox("绘制所有特征的SHAP依赖图", value=False)

        if plot_all:
            plot_all_shap_dependence()
        else:
            plot_single_shap_dependence()


def plot_single_shap_dependence():
    """
    绘制单个选定特征的SHAP依赖图。
    """
    selected_feature = st.selectbox(
        "选择要展示依赖图的特征", st.session_state.selected_columns[1:]
    )
    plot_shap_dependence(selected_feature)


def plot_all_shap_dependence():
    """
    绘制所有特征的SHAP依赖图。
    """
    with st.spinner("正在生成所有特征的SHAP依赖图..."):
        for feature in st.session_state.selected_columns[1:]:
            plot_shap_dependence(feature)


def plot_shap_dependence(feature):
    """
    绘制指定特征的SHAP依赖图。

    Args:
        feature (str): 要绘制依赖图的特征名。
    """
    with st.spinner(f"正在生成 {feature} 的SHAP依赖图..."):
        feature_values, shap_values = calculate_shap_dependence(
            st.session_state.model,
            st.session_state.filtered_df[st.session_state.selected_columns[1:]],
            feature,
        )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=feature_values,
                y=shap_values,
                mode="markers",
                marker=dict(
                    size=8,
                    color=feature_values,
                    colorscale="RdBu",
                    colorbar=dict(title=feature),
                    showscale=True,
                ),
                text=feature_values,
                hoverinfo="text+y",
            )
        )

        fig.update_layout(
            title=f"SHAP依赖图 - {feature}",
            xaxis_title=feature,
            yaxis_title="SHAP值",
            height=600,
            width=800,
        )

        st.plotly_chart(fig)


def display_download_button():
    """
    显示下载分析结果的按钮。
    """
    if st.session_state.filtered_df is None or not st.session_state.selected_columns:
        return

    corr_matrix = st.session_state.filtered_df[st.session_state.selected_columns].corr()
    feature_importance_df = pd.DataFrame(
        {"importance": st.session_state.feature_importance}
    )
    shap_values_df = (
        pd.DataFrame({"shap_value": st.session_state.shap_values})
        if st.session_state.get("use_shap")
        else None
    )

    excel_file = create_excel_download(
        corr_matrix, feature_importance_df, shap_values_df
    )

    st.download_button(
        label="📥 下载分析结果 (Excel)",
        data=excel_file,
        file_name="影响因素分析结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption(
        f"Excel文件包含：相关性热图、特征重要性{' 和SHAP值' if st.session_state.get('use_shap') else ''}。"
    )


if __name__ == "__main__":
    main()
