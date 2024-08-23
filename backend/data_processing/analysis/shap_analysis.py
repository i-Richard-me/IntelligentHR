import shap
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Any, Dict, List, Tuple


def calculate_shap_values(
    model: Any,
    X: pd.DataFrame,
    preprocessor: Any,
    feature_names: List[str],
    problem_type: str,
) -> Dict[str, Any]:
    """
    计算SHAP值并生成SHAP摘要图。

    Args:
        model: 训练好的模型
        X: 原始特征数据
        preprocessor: 数据预处理器
        feature_names: 原始特征名列表
        problem_type: 问题类型 ("classification" 或 "regression")

    Returns:
        包含SHAP值和图表数据的字典
    """
    # 预处理数据
    X_processed = preprocessor.transform(X)

    # 获取预处理后的特征名称
    if hasattr(preprocessor, "get_feature_names_out"):
        processed_feature_names = preprocessor.get_feature_names_out()
    else:
        processed_feature_names = np.array(feature_names)

    # 创建SHAP解释器
    if problem_type == "classification":
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_processed)
        if isinstance(shap_values, list):
            shap_values = shap_values[
                1
            ]  # For binary classification, we use the positive class
        elif shap_values.ndim == 3:
            shap_values = shap_values[
                :, :, 1
            ]  # For binary classification with 3D output
    else:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_processed)

    # 确保shap_values是二维的
    if shap_values.ndim != 2:
        raise ValueError(f"Unexpected SHAP values shape: {shap_values.shape}")

    # 计算特征重要性
    feature_importance = np.abs(shap_values).mean(0)
    feature_importance = pd.Series(
        feature_importance, index=processed_feature_names
    ).sort_values(ascending=False)

    # 创建SHAP摘要图数据
    summary_data = []
    for feature in feature_importance.index:
        feature_shap = shap_values[:, list(processed_feature_names).index(feature)]
        summary_data.append(
            {
                "feature": feature,
                "importance": feature_importance[feature],
                "shap_values": feature_shap.tolist(),
            }
        )

    return {
        "shap_values": shap_values,
        "feature_importance": feature_importance,
        "summary_data": summary_data,
        "processed_feature_names": processed_feature_names,
        "X_processed": X_processed,
    }


def create_shap_summary_plot(
    summary_data: List[Dict[str, Any]], max_display: int = 10
) -> go.Figure:
    """
    创建SHAP摘要图。

    Args:
        summary_data: SHAP摘要数据
        max_display: 显示的最大特征数

    Returns:
        plotly Figure对象
    """
    summary_data = sorted(summary_data, key=lambda x: x["importance"], reverse=True)[
        :max_display
    ]

    fig = go.Figure()

    for data in summary_data:
        fig.add_trace(
            go.Box(
                y0=data["feature"],
                x=data["shap_values"],
                name=data["feature"],
                orientation="h",
                boxmean=True,
                marker_color="lightblue",
                line_color="darkblue",
            )
        )

    fig.update_layout(
        title="SHAP特征重要性摘要图",
        xaxis_title="SHAP值",
        yaxis_title="特征",
        height=max(500, len(summary_data) * 30),
        width=800,
        showlegend=False,
    )

    return fig


def create_shap_importance_plot(
    feature_importance: pd.Series, max_display: int = 20
) -> go.Figure:
    """
    创建SHAP特征重要性图。

    Args:
        feature_importance: 包含特征重要性的pandas Series
        max_display: 显示的最大特征数

    Returns:
        plotly Figure对象
    """
    # 选择前N个最重要的特征
    top_features = feature_importance.nlargest(max_display)

    fig = go.Figure(
        go.Bar(x=top_features.values, y=top_features.index, orientation="h")
    )

    fig.update_layout(
        title="SHAP特征重要性",
        xaxis_title="平均|SHAP值|（特征重要性）",
        yaxis_title="特征",
        height=max(500, len(top_features) * 25),
        width=800,
        yaxis=dict(autorange="reversed"),  # 这会使最重要的特征显示在顶部
    )

    return fig


import numpy as np


def create_shap_dependence_plot(
    shap_values: np.ndarray,
    features: np.ndarray,
    feature_names: np.ndarray,
    selected_feature: str,
) -> go.Figure:
    """
    为选定的特征创建SHAP依赖图。

    Args:
        shap_values: SHAP值数组
        features: 预处理后的特征数据
        feature_names: 预处理后的特征名称数组
        selected_feature: 选定的特征名称

    Returns:
        plotly Figure对象
    """
    feature_index = np.where(feature_names == selected_feature)[0][0]
    feature_value = features[:, feature_index]
    shap_value = shap_values[:, feature_index]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=feature_value,
            y=shap_value,
            mode="markers",
            marker=dict(
                size=8,
                color=feature_value,
                colorscale="RdBu",
                showscale=True,
                colorbar=dict(title=selected_feature),
            ),
            text=[
                f"{selected_feature}: {val}<br>SHAP value: {shap:.2f}"
                for val, shap in zip(feature_value, shap_value)
            ],
            hoverinfo="text",
        )
    )

    fig.update_layout(
        title=f"SHAP Dependence Plot for {selected_feature}",
        xaxis_title=selected_feature,
        yaxis_title="SHAP value",
        width=800,
        height=600,
    )

    return fig
