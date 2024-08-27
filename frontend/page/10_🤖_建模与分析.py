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
    display_linear_regression_settings,
    display_model_selection,
)
from backend.data_processing.analysis.shap_analysis import (
    calculate_shap_values,
    create_shap_summary_plot,
    create_shap_importance_plot,
    create_shap_dependence_plot,
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

            do_model_interpretation = st.checkbox(
                "进行模型解释", value=st.session_state.do_model_interpretation
            )

            if do_model_interpretation != st.session_state.do_model_interpretation:
                st.session_state.do_model_interpretation = do_model_interpretation
                if not do_model_interpretation and "shap_results" in st.session_state:
                    del st.session_state.shap_results

            if st.session_state.do_model_interpretation:
                display_model_interpretation()
    else:
        display_saved_model_selection()
        display_data_upload_and_preview(for_prediction=True)
        if st.session_state.data_validated:
            display_prediction_execution()
            display_prediction_results()

    show_footer()


def display_data_upload_and_preview(for_prediction=False):
    st.markdown("## 数据上传与预览")
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
        st.markdown("## 变量选择")
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
        st.markdown("## 模型训练")
        with st.container(border=True):
            display_data_split_settings()

            if st.button("开始训练模型"):
                with st.spinner("正在训练模型，请稍候..."):
                    try:
                        # 根据模型类型选择相应的参数空间
                        if st.session_state.model_type == "随机森林":
                            param_ranges = st.session_state.rf_param_grid
                            n_trials = st.session_state.rf_n_trials
                        elif st.session_state.model_type == "决策树":
                            param_ranges = st.session_state.dt_param_grid
                            n_trials = None  # 决策树使用网格搜索，不需要n_trials
                        elif st.session_state.model_type == "XGBoost":
                            param_ranges = st.session_state.xgb_param_ranges
                            n_trials = st.session_state.xgb_n_trials
                        elif st.session_state.model_type == "线性回归":
                            param_ranges = None  # 线性回归不需要参数优化
                            n_trials = None
                        else:
                            raise ValueError(
                                f"不支持的模型类型: {st.session_state.model_type}"
                            )

                        st.session_state.model_results = train_model(
                            st.session_state.df,
                            st.session_state.target_column,
                            st.session_state.feature_columns,
                            st.session_state.model_type,
                            st.session_state.problem_type,
                            st.session_state.test_size,
                            param_ranges=param_ranges,
                            n_trials=n_trials,
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

                        if st.session_state.do_model_interpretation:
                            with st.spinner("正在计算模型解释..."):
                                calculate_and_store_shap_values()
                                st.success("模型解释计算完成！")

                    except Exception as e:
                        st.error(f"模型训练过程中出错：{str(e)}")


def display_model_records():
    if not st.session_state.model_records.empty:
        st.markdown("## 模型记录")
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

            # 根据问题类型选择最佳模型
            if st.session_state.problem_type == "classification":
                best_model_index = temp_df["交叉验证分数"].idxmax()
            else:  # regression
                best_model_index = temp_df["测试集分数"].idxmin()  # 使用 MSE，越低越好

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
                        help="表现最好的模型",
                        default=False,
                    ),
                    "交叉验证分数": st.column_config.NumberColumn(
                        "交叉验证分数",
                        format="%.4f",
                        help="对于线性回归模型不使用交叉验证时，此值为训练集 MSE。",
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
                help="对于线性回归模型不使用交叉验证时，此值为训练集 MSE。",
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

    # 为线性回归模型添加 R² 显示
    if (
        st.session_state.problem_type == "regression"
        and st.session_state.model_type == "线性回归"
    ):
        col3, col4 = st.columns(2)
        with col3:
            st.metric(
                label="训练集 R²",
                value=f"{st.session_state.model_results['train_r2']:.4f}",
            )
        with col4:
            st.metric(
                label="测试集 R²",
                value=f"{st.session_state.model_results['test_r2']:.4f}",
            )


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
            tab1, tab2, tab3 = st.tabs(["特征重要性", "SHAP分析", "SHAP依赖图"])

            with tab1:
                st.markdown("### 模型特征重要性")
                display_feature_importance()

            with tab2:
                st.markdown("### SHAP特征重要性分析")
                if "shap_results" not in st.session_state:
                    calculate_and_store_shap_values()

                if "shap_results" in st.session_state:
                    fig = create_shap_importance_plot(
                        st.session_state.shap_results["feature_importance"]
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    with st.expander("SHAP特征重要性解释", expanded=False):
                        st.markdown(
                            """
                        SHAP (SHapley Additive exPlanations) 特征重要性图展示了每个特征对模型预测的平均绝对贡献。

                        - 每个条形代表一个特征。
                        - 条形的长度表示该特征的平均绝对SHAP值，即该特征对模型预测的平均影响程度。
                        - 特征按重要性从上到下排序，最上面的特征对模型预测的影响最大。

                        通过这个图，我们可以直观地看出哪些特征对模型的预测结果影响最大。这有助于我们理解模型的决策依据，
                        并可能为进一步的特征工程或模型优化提供指导。

                        对于线性回归模型，SHAP值直接对应于特征的系数（考虑了特征的尺度）。正的SHAP值表示该特征
                        增加了预测值，而负的SHAP值表示该特征减少了预测值。
                        """
                        )

            with tab3:
                st.markdown("### SHAP依赖图")
                if "shap_results" in st.session_state:
                    processed_feature_names = st.session_state.shap_results[
                        "processed_feature_names"
                    ]
                    selected_feature = st.selectbox(
                        "选择特征", options=processed_feature_names
                    )

                    fig = create_shap_dependence_plot(
                        st.session_state.shap_results["shap_values"],
                        st.session_state.shap_results["X_processed"],
                        np.array(processed_feature_names),
                        selected_feature,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    with st.expander("SHAP依赖图解释", expanded=False):
                        st.markdown(
                            """
                        SHAP依赖图展示了选定特征的值如何影响其SHAP值（即对模型预测的影响）。

                        - X轴表示特征的实际值。
                        - Y轴表示该特征的SHAP值。
                        - 每个点代表一个样本。
                        - 点的颜色表示特征值的大小，红色表示较大的值，蓝色表示较小的值。

                        通过这个图，我们可以观察到：
                        1. 特征值与SHAP值之间的关系是否线性、单调或更复杂。
                        2. 特征值的哪些范围对预测结果有正面或负面影响。
                        3. 是否存在特征值的临界点，在该点附近预测结果发生显著变化。

                        对于线性回归模型，SHAP依赖图通常会显示为一条直线，斜率对应于该特征的系数。
                        这反映了线性回归模型中特征与目标变量之间的线性关系。

                        这有助于我们深入理解特定特征是如何影响模型预测的，对模型的解释和改进都很有价值。
                        """
                        )


def calculate_and_store_shap_values():
    if "shap_results" in st.session_state:
        del st.session_state.shap_results

    with st.spinner("正在计算SHAP值，这可能需要一些时间..."):
        try:
            model_step = (
                "regressor"
                if st.session_state.model_type == "线性回归"
                else "classifier"
            )
            shap_results = calculate_shap_values(
                st.session_state.model_results["model"].named_steps[model_step],
                st.session_state.df[st.session_state.feature_columns],
                st.session_state.model_results["model"].named_steps["preprocessor"],
                st.session_state.feature_columns,
                st.session_state.problem_type,
            )
            st.session_state.shap_results = shap_results
        except Exception as e:
            st.error(f"计算SHAP值时出错：{str(e)}")
            st.error("请检查模型类型和数据是否兼容，或尝试使用其他解释方法。")


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
        if st.session_state.model_type == "线性回归":
            st.caption(
                """
                对于线性回归模型，特征重要性是基于各个特征的系数的绝对值计算的。
                系数的绝对值越大，表示该特征对预测结果的影响越大。
                请注意，这种方法没有考虑特征的尺度，因此在解释时应当结合特征的实际含义和尺度来理解其重要性。
                """
            )
        else:
            st.caption(FEATURE_IMPORTANCE_EXPLANATION)


def display_saved_model_selection():
    st.markdown("## 选择已保存的模型")
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
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("模型类型", model_info["type"])
                with col2:
                    st.metric(
                        "问题类型",
                        "分类" if problem_type == "classification" else "回归",
                    )
                with col3:
                    st.metric("所需特征数量", len(model_info["features"]))

                with st.expander("查看所需特征列表"):
                    features_df = pd.DataFrame(
                        model_info["features"], columns=["特征名称"]
                    )
                    st.dataframe(features_df, use_container_width=True)

                # 显示模型性能指标（如果有的话）
                if "performance" in model_info:
                    st.markdown("### 模型性能")
                    performance = model_info["performance"]
                    if problem_type == "classification":
                        st.metric(
                            "测试集 ROC AUC", f"{performance['test_roc_auc']:.4f}"
                        )
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("测试集 MSE", f"{performance['test_mse']:.4f}")
                        with col2:
                            if "test_r2" in performance:
                                st.metric("测试集 R²", f"{performance['test_r2']:.4f}")

                # 可以添加一个提示，说明当前正在使用的模型类型
                st.info(
                    f"当前使用的是{'分类' if problem_type == 'classification' else '回归'}模型。"
                )

            except Exception as e:
                st.error(f"加载模型时出错: {str(e)}")
                st.error(f"错误类型: {type(e).__name__}")
                st.error(f"模型文件: {selected_model}")
                st.error(f"问题类型: {problem_type}")
                st.warning(
                    "这可能是因为选择的模型与当前版本不兼容，或模型文件已损坏。请尝试重新训练模型。"
                )


def display_prediction_execution():
    if st.session_state.data_validated:
        st.markdown("## 执行预测")
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


main()
