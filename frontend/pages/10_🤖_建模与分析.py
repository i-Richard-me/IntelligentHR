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
from backend.data_processing.analysis.random_forest_trainer import train_random_forest
from backend.data_processing.analysis.decision_tree_trainer import train_decision_tree
from backend.data_processing.analysis.xgboost_trainer import train_xgboost
from backend.data_processing.analysis.ml_explanations import (
    ML_TOOL_INFO,
    CONFUSION_MATRIX_EXPLANATION,
    CLASSIFICATION_REPORT_EXPLANATION,
    FEATURE_IMPORTANCE_EXPLANATION,
)
from backend.data_processing.analysis.model_predictor import (
    ModelPredictor,
    list_available_models,
)
from backend.data_processing.analysis.model_utils import (
    train_model,
    save_model,
    add_model_record,
    initialize_session_state,
    evaluate_model,
    get_feature_importance
)

# Streamlit 页面配置
st.set_page_config(
    page_title="智能HR助手 - 机器学习建模与预测",
    page_icon="🤖",
    layout="wide",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

if 'initialized' not in st.session_state:
    st.session_state.update(initialize_session_state())
    st.session_state.initialized = True


def main():
    initialize_session_state()

    st.title("🤖 机器学习建模与预测")
    st.markdown("---")

    display_info_message()

    # 模式选择
    mode = st.radio("选择操作模式", ["训练新模型", "使用已保存模型"])
    st.session_state.mode = "train" if mode == "训练新模型" else "predict"

    if st.session_state.mode == "train":
        display_model_selection()
        display_data_upload_and_preview()

        if st.session_state.df is not None:
            display_column_selection()
            display_model_training_and_advanced_settings()
            display_model_records()

        if st.session_state.model_results:
            display_results()
            display_feature_importance()
    else:
        display_saved_model_selection()
        display_data_upload_and_preview(for_prediction=True)
        if st.session_state.data_validated:
            display_prediction_execution()
            display_prediction_results()

    show_footer()


def display_info_message():
    st.info(
        """
    **🤖 机器学习建模与预测工具**

    这个工具允许您训练新的机器学习模型或使用已保存的模型进行预测。

    主要功能包括：
    - 数据上传和预览
    - 模型选择和参数设置
    - 模型训练和评估
    - 使用训练好的模型进行预测
    - 结果可视化和下载
    """
    )


def display_model_selection():
    st.markdown('<h2 class="section-title">模型选择</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        st.session_state.model_type = st.radio(
            "选择模型类型",
            ("随机森林", "决策树", "XGBoost"),
            key="model_type_radio",
        )


def display_saved_model_selection():
    st.markdown('<h2 class="section-title">选择已保存的模型</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        available_models = list_available_models()
        selected_model = st.selectbox("选择模型", available_models)

        if selected_model:
            try:
                st.session_state.predictor.load_model(selected_model)
                st.success(f"成功加载模型: {selected_model}")

                model_info = st.session_state.predictor.get_model_info()
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.metric("模型类型", model_info["type"])
                with col2:
                    st.metric("所需特征数量", len(model_info["features"]))

                with st.expander("查看所需特征列表"):
                    features_df = pd.DataFrame(
                        model_info["features"], columns=["特征名称"]
                    )
                    st.dataframe(features_df, use_container_width=True)
            except Exception as e:
                st.error(f"加载模型时出错: {str(e)}")


def display_data_upload_and_preview(for_prediction=False):
    st.markdown('<h2 class="section-title">数据上传与预览</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "上传CSV或Excel文件", type=["csv", "xlsx", "xls"]
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    data = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith((".xls", ".xlsx")):
                    data = pd.read_excel(uploaded_file)
                else:
                    st.error("不支持的文件格式。请上传CSV或Excel文件。")
                    return

                st.session_state.data_validated = False

                if for_prediction:
                    if st.session_state.predictor.model is not None:
                        model_features = set(st.session_state.predictor.original_features)
                        data_features = set(data.columns)
                        missing_features = model_features - data_features
                        extra_features = data_features - model_features

                        if missing_features:
                            st.warning(f"⚠️ 上传的数据缺少以下特征：{', '.join(missing_features)}")
                            return

                        st.session_state.uploaded_data = data
                        st.session_state.data_validated = True
                        st.success("✅ 数据上传成功！")

                        if extra_features:
                            st.info(f"ℹ️ 额外的特征: {', '.join(extra_features)}")
                    else:
                        st.warning("⚠️ 请先选择一个模型，然后再上传数据。")
                        return
                else:
                    st.session_state.df = data
                    st.session_state.data_validated = True
                    st.success("文件上传成功！")

                st.write(f"数据集包含 {len(data)} 行和 {len(data.columns)} 列")
                st.write(data.head())

                with st.expander("查看数据类型信息", expanded=False):
                    st.write(data.dtypes)

            except Exception as e:
                st.error(f"处理文件时出错：{str(e)}")


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
            display_data_split_settings()

            with st.expander("模型参数高级设置"):
                if st.session_state.model_type == "随机森林":
                    display_random_forest_settings()
                elif st.session_state.model_type == "决策树":
                    display_decision_tree_settings()
                else:  # XGBoost
                    display_xgboost_settings()

            if st.button("开始训练模型"):
                with st.spinner("正在训练模型，请稍候..."):
                    try:
                        st.session_state.model_results = train_model(
                            st.session_state.df,
                            st.session_state.target_column,
                            st.session_state.feature_columns,
                            st.session_state.model_type,
                            st.session_state.test_size,
                            param_ranges=st.session_state.custom_param_ranges,
                            n_trials=st.session_state.rf_n_trials if st.session_state.model_type == "随机森林" else st.session_state.xgb_n_trials
                        )
                        st.session_state.model_records = add_model_record(
                            st.session_state.model_records,
                            st.session_state.model_type,
                            st.session_state.model_results
                        )
                        success_message = "模型训练完成！"
                        if "best_trial" in st.session_state.model_results:
                            success_message += f" 最佳参数在第 {st.session_state.model_results['best_trial']} 轮获得。"
                        st.success(success_message)
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
                        <div class="metric-value">{st.session_state.model_results['test_roc_auc']:.4f}</div>
                        <div class="metric-label">测试集 ROC AUC</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("查看最佳模型参数", expanded=False):
                st.json(st.session_state.model_results["best_params"])

            if st.session_state.model_type == "XGBoost":
                label_encoding = st.session_state.model_results.get("label_encoding")
                if label_encoding:
                    with st.expander("查看目标变量编码信息", expanded=False):
                        st.caption(
                            """
                                    ### 目标变量编码对照表

                                    在 XGBoost 模型中，我们对目标变量进行了编码处理。这是因为 XGBoost 要求输入的目标变量为数值型。
                                    下表展示了原始类别与其对应的编码值：
                                    """
                        )

                        encoding_df = pd.DataFrame(
                            list(label_encoding.items()), columns=["原始类别", "编码值"]
                        )
                        st.table(encoding_df)

                        st.caption(
                            """
                                    #### 注意事项：
                                    - 在解释模型输出时，请参考此对照表将数值结果转换回原始类别。
                                    - 编码值的大小并不代表类别的优劣或重要性。
                                    - 如果您计划使用此模型进行预测，请确保使用相同的编码方式处理新数据。
                                    """
                        )

            st.markdown("---")
            st.markdown("#### 混淆矩阵")
            display_confusion_matrix()

            st.markdown("---")
            st.markdown("#### 分类报告")
            st.text(st.session_state.model_results["test_classification_report"])

            with st.expander("分类报告解读", expanded=False):
                st.caption(CLASSIFICATION_REPORT_EXPLANATION)


def display_confusion_matrix():
    cm = st.session_state.model_results["test_confusion_matrix"]
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
        width=400,
        height=400,
    )
    st.plotly_chart(fig)

    with st.expander("混淆矩阵解读", expanded=False):
        st.caption(CONFUSION_MATRIX_EXPLANATION)


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
                height=max(500, len(feature_importance) * 25),
                width=600,
            )
            st.plotly_chart(fig)

            with st.expander("特征重要性解释", expanded=False):
                st.caption(FEATURE_IMPORTANCE_EXPLANATION)


def display_prediction_execution():
    if st.session_state.data_validated:
        st.markdown('<h2 class="section-title">执行预测</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            if st.button("执行预测", type="primary"):
                with st.spinner("正在执行预测..."):
                    try:
                        predictions, probabilities = st.session_state.predictor.predict(
                            st.session_state.uploaded_data
                        )
                        st.session_state.predictions = predictions
                        st.session_state.probabilities = probabilities
                        st.success("✅ 预测完成！")
                    except Exception as e:
                        st.error(f"预测过程中出错: {str(e)}")


def display_prediction_results():
    if (
            st.session_state.predictions is not None
            and st.session_state.probabilities is not None
    ):
        st.markdown('<h2 class="section-title">预测结果</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            results_df = pd.DataFrame(
                {
                    "预测类别": st.session_state.predictions,
                    "预测概率": np.max(st.session_state.probabilities, axis=1),
                }
            )

            st.dataframe(results_df, use_container_width=True)

            # 预测分布可视化
            fig = go.Figure(data=[go.Histogram(x=st.session_state.predictions)])
            fig.update_layout(
                title="预测类别分布", xaxis_title="预测类别", yaxis_title="数量"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 提供下载预测结果的选项
            csv = results_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 下载预测结果",
                data=csv,
                file_name="prediction_results.csv",
                mime="text/csv",
            )


def display_model_records():
    if not st.session_state.model_records.empty:
        st.markdown('<h2 class="section-title">模型记录</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            columns_order = [
                "模型ID",
                "模型类型",
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
                    "模型类型",
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

            save_selected_models(edited_df)


def save_selected_models(edited_df):
    models_to_save = edited_df[edited_df["保存"]]
    if not models_to_save.empty:
        for _, row in models_to_save.iterrows():
            model_id = row["模型ID"]
            model_type = row["模型类型"]
            timestamp = datetime.strptime(row["训练时间"], "%Y-%m-%d %H:%M:%S")
            if (
                    st.session_state.model_results
                    and st.session_state.model_results["model"]
            ):
                file_path = save_model(
                    st.session_state.model_results["model"],
                    model_id,
                    model_type,
                    timestamp
                )
                st.success(f"模型 {model_id} ({model_type}) 已成功保存到 {file_path}")
            else:
                st.warning(f"无法保存模型 {model_id}，模型对象不存在。")


def display_data_split_settings():
    with st.expander("数据划分设置", expanded=False):
        st.markdown("#### 训练集和测试集划分")

        # 使用会话状态来存储当前的test_size值和之前确认的值
        if "current_test_size" not in st.session_state:
            st.session_state.current_test_size = 0.3
        if "confirmed_test_size" not in st.session_state:
            st.session_state.confirmed_test_size = 0.3

        # 滑块用于调整test_size
        new_test_size = st.slider(
            "测试集比例",
            min_value=0.1,
            max_value=0.5,
            value=st.session_state.current_test_size,
            step=0.05,
            help="设置用于测试的数据比例。推荐范围：0.2 - 0.3",
        )

        # 更新当前的test_size值
        st.session_state.current_test_size = new_test_size

        # 添加确认按钮
        if st.button("确认数据划分设置"):
            st.session_state.confirmed_test_size = new_test_size
            st.success(f"数据划分设置已更新。测试集比例：{new_test_size:.2f}")

    # 确保其他部分使用确认后的test_size值
    st.session_state.test_size = st.session_state.confirmed_test_size


def display_random_forest_settings():
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

    st.session_state.rf_n_trials = st.slider(
        "优化迭代次数 (n_trials)",
        min_value=50,
        max_value=500,
        value=st.session_state.rf_n_trials,
        step=10,
        help="增加迭代次数可能提高模型性能，但会显著增加训练时间。",
    )

    if st.button("确认随机森林参数设置"):
        st.session_state.custom_param_ranges = {
            "n_estimators": n_estimators_range,
            "max_depth": max_depth_range,
            "min_samples_split": min_samples_split_range,
            "min_samples_leaf": min_samples_leaf_range,
            "max_features": max_features_options,
        }
        st.success("随机森林参数设置已更新，将在下次模型训练时使用。")

    if st.session_state.rf_n_trials > 300:
        st.warning("注意：设置较大的迭代次数可能会显著增加训练时间。")


def display_decision_tree_settings():
    st.markdown("#### 决策树参数设置")

    def create_param_range(param_name, default_values):
        non_none_values = [v for v in default_values if v is not None]
        min_val, max_val = min(non_none_values), max(non_none_values)
        step = min(
            set(
                non_none_values[i + 1] - non_none_values[i]
                for i in range(len(non_none_values) - 1)
            ),
            default=1,
        )

        col1, col2, col3, col4 = st.columns([3, 3, 3, 2])
        with col1:
            start = st.number_input(f"{param_name} 最小值", value=min_val, step=step)
        with col2:
            end = st.number_input(f"{param_name} 最大值", value=max_val, step=step)
        with col3:
            custom_step = st.number_input(
                f"{param_name} 步长", value=step, min_value=step
            )
        with col4:
            include_none = st.checkbox(
                "包含None", key=f"{param_name}_none", value=None in default_values
            )

        values = list(range(int(start), int(end) + int(custom_step), int(custom_step)))
        if include_none:
            values.append(None)

        return values

    default_params = st.session_state.dt_param_grid
    max_depth = create_param_range("max_depth", default_params["classifier__max_depth"])
    min_samples_split = create_param_range(
        "min_samples_split", default_params["classifier__min_samples_split"]
    )
    min_samples_leaf = create_param_range(
        "min_samples_leaf", default_params["classifier__min_samples_leaf"]
    )
    max_leaf_nodes = create_param_range(
        "max_leaf_nodes", default_params["classifier__max_leaf_nodes"]
    )

    if st.button("确认决策树参数设置"):
        new_param_grid = {
            "classifier__max_depth": max_depth,
            "classifier__min_samples_split": min_samples_split,
            "classifier__min_samples_leaf": min_samples_leaf,
            "classifier__max_leaf_nodes": max_leaf_nodes,
        }

        # 计算参数空间大小
        param_space_size = np.prod([len(v) for v in new_param_grid.values()])

        st.session_state.dt_param_grid = new_param_grid
        st.success(
            f"决策树参数设置已更新，将在下次模型训练时使用。参数空间大小：{param_space_size:,} 种组合。"
        )

        # 可选：添加警告信息
        if param_space_size > 1000000:
            st.warning(
                "警告：参数空间非常大，可能会导致训练时间过长。考虑减少某些参数的范围或增加步长。"
            )


def display_xgboost_settings():
    col1, col2 = st.columns(2)
    with col1:
        n_estimators_range = st.slider(
            "n_estimators 范围",
            min_value=50,
            max_value=1000,
            value=st.session_state.xgb_param_ranges["n_estimators"],
            step=50,
        )
        max_depth_range = st.slider(
            "max_depth 范围",
            min_value=1,
            max_value=15,
            value=st.session_state.xgb_param_ranges["max_depth"],
        )
        learning_rate_range = st.slider(
            "learning_rate 范围",
            min_value=0.01,
            max_value=1.0,
            value=st.session_state.xgb_param_ranges["learning_rate"],
            step=0.01,
        )
    with col2:
        subsample_range = st.slider(
            "subsample 范围",
            min_value=0.5,
            max_value=1.0,
            value=st.session_state.xgb_param_ranges["subsample"],
            step=0.1,
        )
        colsample_bytree_range = st.slider(
            "colsample_bytree 范围",
            min_value=0.5,
            max_value=1.0,
            value=st.session_state.xgb_param_ranges["colsample_bytree"],
            step=0.1,
        )
        min_child_weight_range = st.slider(
            "min_child_weight 范围",
            min_value=1,
            max_value=20,
            value=st.session_state.xgb_param_ranges["min_child_weight"],
        )

    st.session_state.xgb_n_trials = st.slider(
        "优化迭代次数 (n_trials)",
        min_value=100,
        max_value=2000,
        value=st.session_state.xgb_n_trials,
        step=50,
        help="增加迭代次数可能提高模型性能，但会显著增加训练时间。",
    )

    if st.button("确认XGBoost参数设置"):
        st.session_state.xgb_param_ranges = {
            "n_estimators": n_estimators_range,
            "max_depth": max_depth_range,
            "learning_rate": learning_rate_range,
            "subsample": subsample_range,
            "colsample_bytree": colsample_bytree_range,
            "min_child_weight": min_child_weight_range,
            "reg_alpha": st.session_state.xgb_param_ranges["reg_alpha"],
            "reg_lambda": st.session_state.xgb_param_ranges["reg_lambda"],
        }
        st.success("XGBoost参数设置已更新，将在下次模型训练时使用。")

    if st.session_state.xgb_n_trials > 500:
        st.warning("注意：设置较大的迭代次数可能会显著增加训练时间。")


if __name__ == "__main__":
    main()
