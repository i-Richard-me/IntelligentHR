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
from backend.data_processing.analysis.ml_explanations import (
    ML_TOOL_INFO,
    CONFUSION_MATRIX_EXPLANATION,
    CLASSIFICATION_REPORT_EXPLANATION,
    FEATURE_IMPORTANCE_EXPLANATION,
    REGRESSION_METRICS_EXPLANATION,
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
    get_feature_importance,
)
from backend.data_processing.analysis.ml_components import (
    display_info_message,
    display_data_split_settings,
    display_random_forest_settings,
    display_decision_tree_settings,
    display_xgboost_settings,
)

# Streamlit 页面配置
st.set_page_config(
    page_title="智能HR助手 - 机器学习建模与预测",
    page_icon="🤖",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

if "initialized" not in st.session_state:
    st.session_state.update(initialize_session_state())
    st.session_state.initialized = True


def display_operation_settings():
    st.markdown("## 操作设置")
    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            mode = st.radio(
                "选择操作模式",
                options=["训练新模型", "使用已保存模型"],
                index=0 if st.session_state.mode == "train" else 1,
                key="mode_radio",
            )
            st.session_state.mode = "train" if mode == "训练新模型" else "predict"

        with col2:
            problem_type = st.radio(
                "选择问题类型",
                options=["分类问题", "回归问题"],
                index=0 if st.session_state.problem_type == "classification" else 1,
                key="problem_type_radio",
            )
            st.session_state.problem_type = (
                "classification" if problem_type == "分类问题" else "regression"
            )

    # 根据选择显示相应的提示信息
    if st.session_state.mode == "train":
        st.info("您选择了训练新模型。请上传数据并设置模型参数。")
    else:
        st.info(
            f"您选择了使用已保存的{'分类' if st.session_state.problem_type == 'classification' else '回归'}模型进行预测。请选择模型并上传预测数据。"
        )


def main():
    initialize_session_state()

    st.title("🤖 机器学习建模与预测")
    st.markdown("---")

    display_info_message()
    display_operation_settings()

    if st.session_state.mode == "train":
        display_data_upload_and_preview()
        if st.session_state.df is not None:
            display_column_selection()
            display_model_selection()
            display_model_training_and_advanced_settings()
            display_model_records()

        if st.session_state.model_results:
            display_results()
            display_model_interpretation()
    else:
        display_saved_model_selection()
        display_data_upload_and_preview(for_prediction=True)
        if st.session_state.data_validated:
            display_prediction_execution()
            display_prediction_results()

    show_footer()


def display_model_selection():
    st.markdown("## 模型选择")
    with st.container(border=True):
        model_options = ["随机森林", "决策树", "XGBoost"]

        st.session_state.model_type = st.radio(
            "选择模型类型",
            model_options,
            key="model_type_radio",
        )


def display_saved_model_selection():
    st.markdown(
        '<h2 class="section-title">选择已保存的模型</h2>', unsafe_allow_html=True
    )
    with st.container(border=True):
        problem_type = (
            "classification"
            if st.session_state.problem_type == "classification"
            else "regression"
        )
        available_models = list_available_models(problem_type=problem_type)
        selected_model = st.selectbox("选择模型", available_models)

        if selected_model:
            try:
                st.session_state.predictor.load_model(selected_model, problem_type)
                st.success(f"成功加载模型: {selected_model}")

                model_info = st.session_state.predictor.get_model_info()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("模型类型", model_info["type"])
                with col2:
                    st.metric("所需特征数量", len(model_info["features"]))

                with st.expander("查看所需特征列表"):
                    features_df = pd.DataFrame(
                        model_info["features"], columns=["特征名称"]
                    )
                    st.dataframe(features_df, use_container_width=True)

                # 可以添加一个提示，说明当前正在使用的模型类型
                st.info(
                    f"当前使用的是{'分类' if problem_type == 'classification' else '回归'}模型。"
                )

            except Exception as e:
                st.error(f"加载模型时出错: {str(e)}")
                st.warning(
                    "这可能是因为选择的模型与当前版本不兼容。请尝试重新训练模型。"
                )


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
                        model_features = set(
                            st.session_state.predictor.original_features
                        )
                        data_features = set(data.columns)
                        missing_features = model_features - data_features
                        extra_features = data_features - model_features

                        if missing_features:
                            st.warning(
                                f"⚠️ 上传的数据缺少以下特征：{', '.join(missing_features)}"
                            )
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

            # 验证问题类型
            if st.session_state.problem_type == "classification":
                if st.session_state.df[st.session_state.target_column].dtype in [
                    "int64",
                    "float64",
                ]:
                    unique_values = st.session_state.df[
                        st.session_state.target_column
                    ].nunique()
                    if unique_values > 10:
                        st.warning(
                            "目标变量看起来像是连续值。您可能需要选择回归问题而不是分类问题。"
                        )
            else:  # regression
                if st.session_state.df[st.session_state.target_column].dtype not in [
                    "int64",
                    "float64",
                ]:
                    st.warning("目标变量不是数值类型。回归问题需要数值类型的目标变量。")


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
                            st.session_state.problem_type,
                            st.session_state.test_size,
                            param_ranges=st.session_state.custom_param_ranges,
                            n_trials=(
                                st.session_state.rf_n_trials
                                if st.session_state.model_type == "随机森林"
                                else st.session_state.xgb_n_trials
                            ),
                        )
                        st.session_state.model_records = add_model_record(
                            st.session_state.model_records,
                            st.session_state.model_type,
                            st.session_state.problem_type,
                            st.session_state.model_results,
                        )
                        success_message = "模型训练完成！"
                        if "best_trial" in st.session_state.model_results:
                            success_message += f" 最佳参数在第 {st.session_state.model_results['best_trial']} 轮获得。"
                        st.success(success_message)
                    except Exception as e:
                        st.error(f"模型训练过程中出错：{str(e)}")


def display_results():
    if st.session_state.model_results:
        st.markdown("## 模型结果")

        with st.container(border=True):
            if st.session_state.problem_type == "classification":
                tab1, tab2, tab3 = st.tabs(["模型性能概览", "混淆矩阵", "分类报告"])
            else:
                tab1, tab2 = st.tabs(["模型性能概览", "残差图"])

            with tab1:
                display_model_performance_overview()

            if st.session_state.problem_type == "classification":
                with tab2:
                    display_confusion_matrix()
                with tab3:
                    display_classification_report()
            else:
                with tab2:
                    display_residual_plot()


def display_model_performance_overview():
    st.markdown("### 模型性能概览")
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.problem_type == "classification":
            st.metric(
                label="交叉验证平均 ROC AUC",
                value=f"{st.session_state.model_results['cv_mean_score']:.4f}",
            )
        else:
            st.metric(
                label="交叉验证平均 MSE",
                value=f"{st.session_state.model_results['cv_mean_score']:.4f}",
            )
    with col2:
        if st.session_state.problem_type == "classification":
            st.metric(
                label="测试集 ROC AUC",
                value=f"{st.session_state.model_results['test_roc_auc']:.4f}",
            )
        else:
            st.metric(
                label="测试集 MSE",
                value=f"{st.session_state.model_results['test_mse']:.4f}",
            )

    with st.expander("查看最佳模型参数", expanded=False):
        st.json(st.session_state.model_results["best_params"])

    if (
        st.session_state.model_type == "XGBoost"
        and st.session_state.problem_type == "classification"
    ):
        display_xgboost_label_encoding()


def display_confusion_matrix():
    st.markdown("### 混淆矩阵")
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
        xaxis_title="预测类别",
        yaxis_title="实际类别",
        width=400,
        height=400,
        margin=dict(t=40),
    )
    st.plotly_chart(fig)

    with st.expander("混淆矩阵解读", expanded=False):
        st.caption(CONFUSION_MATRIX_EXPLANATION)


def display_classification_report():
    st.markdown("### 分类报告")
    st.text(st.session_state.model_results["test_classification_report"])

    with st.expander("分类报告解读", expanded=False):
        st.caption(CLASSIFICATION_REPORT_EXPLANATION)


def display_residual_plot():
    st.markdown("### 残差图")
    y_test = st.session_state.model_results["y_test"]
    y_pred = st.session_state.model_results["y_pred"]
    residuals = y_test - y_pred

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=y_pred, y=residuals, mode="markers"))
    fig.update_layout(
        title="残差图", xaxis_title="预测值", yaxis_title="残差", width=600, height=400
    )
    st.plotly_chart(fig)

    with st.expander("残差图解读", expanded=False):
        st.caption(REGRESSION_METRICS_EXPLANATION)


def display_xgboost_label_encoding():
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


def display_model_interpretation():
    if (
        st.session_state.model_results
        and "feature_importance" in st.session_state.model_results
    ):
        st.markdown("## 模型解释")

        with st.container(border=True):
            (tab1,) = st.tabs(["特征重要性"])

            with tab1:
                st.markdown("### 模型特征重要性")
                display_feature_importance()


def display_feature_importance():
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
        xaxis_title="重要性得分",
        yaxis_title="特征",
        height=max(500, len(feature_importance) * 25),
        width=600,
        margin=dict(t=40),
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
                        predictions = st.session_state.predictor.predict(
                            st.session_state.uploaded_data
                        )
                        st.session_state.predictions = predictions
                        if st.session_state.predictor.problem_type == "classification":
                            probabilities = st.session_state.predictor.predict_proba(
                                st.session_state.uploaded_data
                            )
                            st.session_state.probabilities = probabilities
                        st.success("✅ 预测完成！")
                    except Exception as e:
                        st.error(f"预测过程中出错: {str(e)}")


def display_prediction_results():
    if st.session_state.predictions is not None:
        st.markdown("## 预测结果")

        with st.container(border=True):
            if st.session_state.predictor.problem_type == "classification":
                # 预测类别分布
                st.markdown("### 预测类别分布")
                fig = go.Figure(data=[go.Histogram(x=st.session_state.predictions)])
                fig.update_layout(
                    xaxis_title="预测类别",
                    yaxis_title="数量",
                    height=400,
                    margin=dict(t=40),
                )
                st.plotly_chart(fig, use_container_width=True)

                # 预测结果预览
                st.markdown("### 预测结果预览")
                results_df = pd.DataFrame(
                    {
                        "预测类别": st.session_state.predictions,
                        "预测概率": np.max(st.session_state.probabilities, axis=1),
                    }
                )
            else:
                # 回归问题的预测分布
                st.markdown("### 预测值分布")
                fig = go.Figure(data=[go.Histogram(x=st.session_state.predictions)])
                fig.update_layout(
                    xaxis_title="预测值",
                    yaxis_title="数量",
                    height=400,
                    margin=dict(t=40),
                )
                st.plotly_chart(fig, use_container_width=True)

                # 预测结果预览
                st.markdown("### 预测结果预览")
                results_df = pd.DataFrame(
                    {
                        "预测值": st.session_state.predictions,
                    }
                )

            st.dataframe(results_df, use_container_width=True)

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
                "问题类型",
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
                    "问题类型",
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
            model_type = row["模型类型"]
            problem_type = (
                "classification" if row["问题类型"] == "分类" else "regression"
            )
            timestamp = datetime.strptime(row["训练时间"], "%Y-%m-%d %H:%M:%S")
            if (
                st.session_state.model_results
                and st.session_state.model_results["model"]
            ):
                file_path = save_model(
                    st.session_state.model_results["model"],
                    model_type,
                    problem_type,
                    timestamp,
                )
                st.success(
                    f"模型 {model_type} ({problem_type}) 已成功保存到 {file_path}"
                )
            else:
                st.warning(f"无法保存模型 {model_type}，模型对象不存在。")


if __name__ == "__main__":
    main()
