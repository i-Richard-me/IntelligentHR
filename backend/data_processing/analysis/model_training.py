import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from backend.data_processing.analysis.model_utils import (
    train_model,
    save_model,
    add_model_record,
    evaluate_model,
    get_feature_importance,
)
from backend.data_processing.analysis.shap_analysis import (
    calculate_shap_values,
)
from backend.data_processing.analysis.visualization import (
    create_confusion_matrix_plot,
    create_residual_plot,
    create_feature_importance_plot,
    create_prediction_distribution_plot,
    create_shap_importance_plot,
    create_shap_dependence_plot,
)
from backend.data_processing.analysis.model_predictor import ModelPredictor
from backend.data_processing.analysis.ml_components import (
    display_info_message,
    display_data_split_settings,
    display_random_forest_settings,
    display_decision_tree_settings,
    display_xgboost_settings,
    display_linear_regression_settings,
    display_model_selection,
    display_preprocessing_settings,
)
from backend.data_processing.analysis.ml_explanations import (
    CONFUSION_MATRIX_EXPLANATION,
    CLASSIFICATION_REPORT_EXPLANATION,
    REGRESSION_METRICS_EXPLANATION,
    ML_TOOL_INFO,
    FEATURE_IMPORTANCE_EXPLANATION,
    SHAP_FEATURE_IMPORTANCE_EXPLANATION,
    SHAP_DEPENDENCE_PLOT_EXPLANATION,
    LINEAR_REGRESSION_FEATURE_IMPORTANCE_EXPLANATION,
    XGBOOST_LABEL_ENCODING_EXPLANATION,
)


def display_data_upload_and_preview(for_prediction=False):
    """显示数据上传和预览界面"""
    st.markdown("## 数据上传与预览")
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "上传CSV或Excel文件", type=["csv", "xlsx", "xls"]
        )

        if uploaded_file is not None:
            try:
                data = (
                    pd.read_csv(uploaded_file)
                    if uploaded_file.name.endswith(".csv")
                    else pd.read_excel(uploaded_file)
                )

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
    """显示列选择界面"""
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
    """显示模型训练和高级设置界面"""
    if (
        st.session_state.df is not None
        and st.session_state.target_column
        and st.session_state.feature_columns
    ):
        st.markdown("## 模型训练")
        with st.container(border=True):
            display_data_split_settings()
            display_preprocessing_settings()

            if st.button("开始训练模型"):
                with st.spinner("正在训练模型，请稍候..."):
                    try:
                        # 根据模型类型选择相应的参数空间
                        param_ranges, n_trials = get_model_params()

                        st.session_state.model_results = train_model(
                            st.session_state.df,
                            st.session_state.target_column,
                            st.session_state.feature_columns,
                            st.session_state.model_type,
                            st.session_state.problem_type,
                            st.session_state.test_size,
                            param_ranges=param_ranges,
                            n_trials=n_trials,
                            numeric_preprocessor=st.session_state.numeric_preprocessor,
                            categorical_preprocessor=st.session_state.categorical_preprocessor,
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


def get_model_params():
    """获取模型参数"""
    if st.session_state.model_type == "随机森林":
        return st.session_state.rf_param_grid, st.session_state.rf_n_trials
    elif st.session_state.model_type == "决策树":
        return st.session_state.dt_param_grid, None
    elif st.session_state.model_type == "XGBoost":
        return st.session_state.xgb_param_ranges, st.session_state.xgb_n_trials
    elif st.session_state.model_type == "线性回归":
        return None, None
    else:
        raise ValueError(f"不支持的模型类型: {st.session_state.model_type}")


def display_model_records():
    """显示模型记录"""
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
            best_model_index = (
                temp_df["交叉验证分数"].idxmax()
                if st.session_state.problem_type == "classification"
                else temp_df["交叉验证分数"].idxmin()
            )
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
                        help="对于线性回归模型不使用交叉验证，此值为训练集 MSE。",
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
    """保存选中的模型"""
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
    """显示模型结果"""
    if st.session_state.model_results:
        st.markdown("## 模型结果")

        with st.container(border=True):
            if st.session_state.problem_type == "classification":
                tabs = ["模型性能概览"]
                if st.session_state.split_test_set:
                    tabs.extend(["混淆矩阵", "分类报告"])
            else:
                tabs = ["模型性能概览"]
                if st.session_state.split_test_set:
                    tabs.append("残差图")

            tab_contents = st.tabs(tabs)

            with tab_contents[0]:
                display_model_performance_overview()

            if st.session_state.split_test_set:
                if st.session_state.problem_type == "classification":
                    with tab_contents[1]:
                        display_confusion_matrix()
                    with tab_contents[2]:
                        display_classification_report()
                elif st.session_state.problem_type == "regression":
                    with tab_contents[1]:
                        display_residual_plot()


def display_model_performance_overview():
    """显示模型性能概览"""
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
    
    if st.session_state.split_test_set:
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
        if st.session_state.split_test_set:
            with col4:
                st.metric(
                    label="测试集 R²",
                    value=f"{st.session_state.model_results['test_r2']:.4f}",
                )

    if not st.session_state.split_test_set:
        st.info("模型使用全部数据进行训练，没有单独的测试集评估。")


def display_confusion_matrix():
    """显示混淆矩阵"""
    st.markdown("### 混淆矩阵")
    cm = st.session_state.model_results["test_confusion_matrix"]
    fig = create_confusion_matrix_plot(cm)
    st.plotly_chart(fig)

    with st.expander("混淆矩阵解读", expanded=False):
        st.caption(CONFUSION_MATRIX_EXPLANATION)


def display_classification_report():
    """显示分类报告"""
    st.markdown("### 分类报告")
    st.text(st.session_state.model_results["test_classification_report"])

    with st.expander("分类报告解读", expanded=False):
        st.caption(CLASSIFICATION_REPORT_EXPLANATION)


def display_residual_plot():
    """显示残差图"""
    st.markdown("### 残差图")
    y_test = st.session_state.model_results["y_test"]
    y_pred = st.session_state.model_results["y_pred"]
    fig = create_residual_plot(y_test, y_pred)
    st.plotly_chart(fig)

    with st.expander("残差图解读", expanded=False):
        st.caption(REGRESSION_METRICS_EXPLANATION)


def display_model_interpretation():
    """显示模型解释"""
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
                        st.markdown(SHAP_FEATURE_IMPORTANCE_EXPLANATION)

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
                        st.markdown(SHAP_DEPENDENCE_PLOT_EXPLANATION)


def calculate_and_store_shap_values():
    """计算并存储SHAP值"""
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
    """显示特征重要性"""
    feature_importance = st.session_state.model_results[
        "feature_importance"
    ].sort_values(ascending=True)
    fig = create_feature_importance_plot(feature_importance)
    st.plotly_chart(fig)

    with st.expander("特征重要性解释", expanded=False):
        if st.session_state.model_type == "线性回归":
            st.caption(LINEAR_REGRESSION_FEATURE_IMPORTANCE_EXPLANATION)
        else:
            st.caption(FEATURE_IMPORTANCE_EXPLANATION)
