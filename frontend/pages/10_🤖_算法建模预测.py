import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import os
import joblib
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.data_processing.analysis.model_trainer import (
    train_and_evaluate_model,
    encode_categorical_variables,
)

# Streamlit 页面配置
st.set_page_config(
    page_title="智能HR助手 - 机器学习建模",
    page_icon="🤖",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


# 初始化会话状态
def initialize_session_state():
    default_states = {
        "df": None,
        "model_results": None,
        "target_column": None,
        "feature_columns": None,
        "param_ranges": {
            "n_estimators": (10, 200),
            "max_depth": (5, 30),
            "min_samples_split": (2, 20),
            "min_samples_leaf": (1, 20),
            "max_features": ["sqrt", "log2"],
        },
        "custom_param_ranges": None,
        "model_records": pd.DataFrame(
            columns=["模型ID", "训练时间", "参数", "交叉验证分数", "测试集分数"]
        ),
    }

    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session_state()


def main():
    st.title("🤖 机器学习建模")
    st.markdown("---")

    display_info_message()
    display_workflow()

    uploaded_file = upload_file()
    if uploaded_file is None:
        return

    display_data_preview()
    display_column_selection()
    display_model_training_and_advanced_settings()
    display_model_records()
    display_results()
    display_feature_importance()

    show_footer()


def display_info_message():
    st.info(
        """
        **🤖 机器学习建模工具**

        这个工具允许您上传数据，选择目标变量和特征，然后使用随机森林分类器进行机器学习建模。

        主要功能包括：
        - 数据上传和预览
        - 目标变量和特征选择
        - 自定义模型参数设置
        - 自动化的模型训练和优化
        - 模型性能评估
        - 特征重要性可视化
        - 模型记录跟踪

        该工具使用交叉验证和独立的验证集来评估模型性能，确保结果的可靠性。
        """
    )


def display_workflow():
    with st.expander("📋 查看机器学习建模工作流程", expanded=False):
        st.markdown(
            '<h2 class="section-title">机器学习建模工作流程</h2>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            1. **数据上传**: 上传包含目标变量和特征的CSV或Excel文件。
            2. **数据预览**: 查看数据的基本信息和前几行内容。
            3. **变量选择**: 选择目标变量和用于建模的特征。
            4. **参数设置**: 可选择调整模型参数搜索范围。
            5. **模型训练**: 使用随机森林分类器进行建模，包括自动化的参数优化。
            6. **性能评估**: 展示交叉验证和验证集上的模型性能。
            7. **特征重要性**: 可视化展示各个特征对模型的重要程度。
            8. **结果解释**: 提供模型结果的简要解释和建议。
            9. **模型记录**: 跟踪并比较不同参数设置下的模型性能。
            """
        )


def upload_file():
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
                return st.session_state.df

            except Exception as e:
                st.error(f"处理文件时出错：{str(e)}")
                return None

    return None


def display_data_preview():
    if st.session_state.df is not None:
        st.markdown('<h2 class="section-title">数据预览</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            st.write(
                f"数据集包含 {len(st.session_state.df)} 行和 {len(st.session_state.df.columns)} 列"
            )
            st.write(st.session_state.df.head())

            with st.expander("查看数据类型信息", expanded=False):
                st.write(st.session_state.df.dtypes)


def display_column_selection():
    if st.session_state.df is not None:
        st.markdown('<h2 class="section-title">变量选择</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            st.session_state.target_column = st.selectbox(
                "选择目标变量",
                options=st.session_state.df.columns,
                key="target_column_select",
            )
            with st.expander("选择特征变量", expanded=False):
                st.session_state.feature_columns = st.multiselect(
                    "选择特征变量",
                    options=[
                        col
                        for col in st.session_state.df.columns
                        if col != st.session_state.target_column
                    ],
                    default=[
                        col
                        for col in st.session_state.df.columns
                        if col != st.session_state.target_column
                    ],
                    key="feature_columns_select",
                )


def display_model_training_and_advanced_settings():
    if (
        st.session_state.df is not None
        and st.session_state.target_column
        and st.session_state.feature_columns
    ):
        st.markdown('<h2 class="section-title">模型训练</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            with st.expander("高级设置"):
                col1, col2 = st.columns(2)
                with col1:
                    n_estimators_range = st.slider(
                        "n_estimators 范围",
                        min_value=10,
                        max_value=500,
                        value=st.session_state.param_ranges["n_estimators"],
                        step=10,
                    )
                    max_depth_range = st.slider(
                        "max_depth 范围",
                        min_value=1,
                        max_value=50,
                        value=st.session_state.param_ranges["max_depth"],
                    )
                with col2:
                    min_samples_split_range = st.slider(
                        "min_samples_split 范围",
                        min_value=2,
                        max_value=30,
                        value=st.session_state.param_ranges["min_samples_split"],
                    )
                    min_samples_leaf_range = st.slider(
                        "min_samples_leaf 范围",
                        min_value=1,
                        max_value=30,
                        value=st.session_state.param_ranges["min_samples_leaf"],
                    )

                max_features_options = st.multiselect(
                    "max_features 选项",
                    options=["sqrt", "log2"]
                    + list(range(1, len(st.session_state.feature_columns) + 1)),
                    default=st.session_state.param_ranges["max_features"],
                )

                if st.button("确认参数设置"):
                    st.session_state.custom_param_ranges = {
                        "n_estimators": n_estimators_range,
                        "max_depth": max_depth_range,
                        "min_samples_split": min_samples_split_range,
                        "min_samples_leaf": min_samples_leaf_range,
                        "max_features": max_features_options,
                    }
                    st.success("参数设置已更新，将在下次模型训练时使用。")

            if st.button("开始训练模型"):
                with st.spinner("正在训练模型，请稍候..."):
                    try:
                        # 处理分类变量
                        categorical_columns = (
                            st.session_state.df[st.session_state.feature_columns]
                            .select_dtypes(include=["object"])
                            .columns
                        )
                        if len(categorical_columns) > 0:
                            st.session_state.df = encode_categorical_variables(
                                st.session_state.df, categorical_columns
                            )
                            # 更新特征列名，使用编码后的列名
                            st.session_state.feature_columns = [
                                (
                                    col
                                    if col not in categorical_columns
                                    else f"{col}_encoded"
                                )
                                for col in st.session_state.feature_columns
                            ]

                        param_ranges = (
                            st.session_state.custom_param_ranges
                            if st.session_state.custom_param_ranges
                            else st.session_state.param_ranges
                        )

                        st.session_state.model_results = train_and_evaluate_model(
                            st.session_state.df,
                            st.session_state.target_column,
                            st.session_state.feature_columns,
                            param_ranges=param_ranges,
                        )

                        # 添加新的模型记录
                        new_record = pd.DataFrame(
                            {
                                "模型ID": [
                                    f"Model_{len(st.session_state.model_records) + 1}"
                                ],
                                "训练时间": [
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                ],
                                "参数": [
                                    str(st.session_state.model_results["best_params"])
                                ],
                                "交叉验证分数": [
                                    st.session_state.model_results["cv_mean_score"]
                                ],
                                "测试集分数": [
                                    st.session_state.model_results["val_roc_auc"]
                                ],
                            }
                        )
                        st.session_state.model_records = pd.concat(
                            [st.session_state.model_records, new_record],
                            ignore_index=True,
                        )

                        st.success("模型训练完成！")
                    except Exception as e:
                        st.error(f"模型训练过程中出错：{str(e)}")


def display_results():
    if st.session_state.model_results:
        st.markdown('<h2 class="section-title">模型结果</h2>', unsafe_allow_html=True)

        st.markdown(
            """
        <style>
        .metric-card {
            border: 1px solid #e1e4e8;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            background-color: #f6f8fa;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #0366d6;
        }
        .metric-label {
            font-size: 16px;
            color: #586069;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("#### 模型性能概览")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value">{st.session_state.model_results['cv_mean_score']:.4f}</div>
                        <div class="metric-label">交叉验证平均 ROC AUC</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value">{st.session_state.model_results['val_roc_auc']:.4f}</div>
                        <div class="metric-label">验证集 ROC AUC</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("查看最佳模型参数", expanded=False):
                st.json(st.session_state.model_results["best_params"])

            st.markdown("---")
            st.markdown("#### 混淆矩阵")
            cm = st.session_state.model_results["val_confusion_matrix"]
            cm_sum = np.sum(cm)
            cm_percentages = cm / cm_sum * 100

            fig = go.Figure(
                data=go.Heatmap(
                    z=cm_percentages,
                    x=["预测: 0", "预测: 1"],
                    y=["实际: 0", "实际: 1"],
                    hoverongaps=False,
                    colorscale="Blues",
                    text=[
                        [f"{v:.1f}%<br>({cm[i][j]})" for j, v in enumerate(row)]
                        for i, row in enumerate(cm_percentages)
                    ],
                    texttemplate="%{text}",
                    textfont={"size": 14},
                )
            )
            fig.update_layout(
                title="混淆矩阵 (百分比和实际数量)",
                xaxis_title="预测类别",
                yaxis_title="实际类别",
                width=500,
                height=500,
            )
            st.plotly_chart(fig)

            with st.expander("混淆矩阵解读", expanded=False):
                st.caption(
                    """
                混淆矩阵展示了模型在各个类别上的预测情况：
                
                - 左上角：正确预测为负类的样本数（真负例，TN）
                - 右上角：错误预测为正类的样本数（假正例，FP）
                - 左下角：错误预测为负类的样本数（假负例，FN）
                - 右下角：正确预测为正类的样本数（真正例，TP）
                
                理想情况下，对角线上的数字（TN和TP）应该较大，而非对角线上的数字（FP和FN）应该较小。
                
                这个矩阵可以帮助我们理解模型在哪些类别上表现较好或较差，从而针对性地改进模型或调整决策阈值。
                """
                )

            st.markdown("---")
            st.markdown("#### 分类报告")
            st.text(st.session_state.model_results["val_classification_report"])

            with st.expander("分类报告解读", expanded=False):
                st.caption(
                    """
                分类报告提供了每个类别的详细性能指标：
                
                - Precision（精确率）：预测为正例中实际为正例的比例
                - Recall（召回率）：实际为正例中被正确预测的比例
                - F1-score：精确率和召回率的调和平均数
                - Support：每个类别的样本数量
                
                'macro avg' 是所有类别的简单平均，'weighted avg' 是考虑了每个类别样本数量的加权平均。
                
                这些指标可以帮助我们全面评估模型在各个类别上的表现，特别是在处理不平衡数据集时。
                """
                )


def display_feature_importance():
    if (
        st.session_state.model_results
        and "feature_importance" in st.session_state.model_results
    ):
        st.markdown('<h2 class="section-title">特征重要性</h2>', unsafe_allow_html=True)

        with st.container(border=True):
            feature_importance = st.session_state.model_results[
                "feature_importance"
            ].sort_values(ascending=True)
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=feature_importance.values,
                        y=feature_importance.index,
                        orientation="h",
                    )
                ]
            )
            fig.update_layout(
                title="特征重要性",
                xaxis_title="重要性得分",
                yaxis_title="特征",
                height=max(500, len(feature_importance) * 20),
                width=800,
            )
            st.plotly_chart(fig)

            with st.expander("特征重要性解释", expanded=False):
                st.caption(
                    """
                特征重要性图展示了模型中各个特征的相对重要性：

                - 重要性得分反映了每个特征对模型预测的贡献程度。
                - 得分越高，表示该特征在模型决策中的影响越大。
                - 这个排序可以帮助我们识别最关键的预测因素。

                注意事项：
                - 特征重要性不表示因果关系，只反映预测能力。
                - 高度相关的特征可能会分散重要性得分。
                - 不同类型的模型可能会产生不同的特征重要性排序。
                - 解释时应结合领域知识和其他分析方法。

                利用特征重要性，我们可以：
                1. 聚焦于最重要的特征，优化数据收集和处理。
                2. 简化模型，可能去除不太重要的特征。
                3. 获得对预测过程的洞察，提升模型可解释性。
                4. 指导进一步的特征工程和选择。
                """
                )


def save_model(model, model_id, timestamp):
    save_path = os.path.join("data", "ml_models")
    os.makedirs(save_path, exist_ok=True)
    file_name = f"Model_{timestamp.strftime('%Y%m%d_%H%M%S')}.joblib"
    file_path = os.path.join(save_path, file_name)
    joblib.dump(model, file_path)
    st.success(f"模型 {model_id} 已成功保存到 {file_path}")


def display_model_records():
    if not st.session_state.model_records.empty:
        st.markdown('<h2 class="section-title">模型记录</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            columns_order = [
                "模型ID",
                "交叉验证分数",
                "测试集分数",
                "最佳模型",
                "保存",
                "训练时间",
                "参数",
            ]
            temp_df = st.session_state.model_records.reindex(columns=columns_order)
            temp_df["保存"] = False
            temp_df["最佳模型"] = False

            best_model_index = temp_df["交叉验证分数"].idxmax()
            temp_df.loc[best_model_index, "最佳模型"] = True

            edited_df = st.data_editor(
                temp_df,
                column_config={
                    "保存": st.column_config.CheckboxColumn(
                        "保存",
                        help="选择要保存的模型",
                        default=False,
                    ),
                    "最佳模型": st.column_config.CheckboxColumn(
                        "最佳模型",
                        help="交叉验证分数最高的模型",
                        default=False,
                    ),
                    "交叉验证分数": st.column_config.NumberColumn(
                        "交叉验证分数",
                        format="%.4f",
                    ),
                    "测试集分数": st.column_config.NumberColumn(
                        "测试集分数",
                        format="%.4f",
                    ),
                },
                disabled=[
                    "模型ID",
                    "训练时间",
                    "参数",
                    "交叉验证分数",
                    "测试集分数",
                    "最佳模型",
                ],
                hide_index=True,
                column_order=columns_order,
                use_container_width=True,
            )

            models_to_save = edited_df[edited_df["保存"]]
            if not models_to_save.empty:
                for _, row in models_to_save.iterrows():
                    model_id = row["模型ID"]
                    timestamp = datetime.strptime(row["训练时间"], "%Y-%m-%d %H:%M:%S")
                    if (
                        st.session_state.model_results
                        and st.session_state.model_results["model"]
                    ):
                        save_model(
                            st.session_state.model_results["model"], model_id, timestamp
                        )
                    else:
                        st.warning(f"无法保存模型 {model_id}，模型对象不存在。")


if __name__ == "__main__":
    main()
