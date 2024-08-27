import streamlit as st
import pandas as pd
import numpy as np
from backend.data_processing.analysis.model_predictor import (
    ModelPredictor,
    list_available_models,
)
from backend.data_processing.analysis.visualization import (
    create_prediction_distribution_plot,
)


def display_saved_model_selection():
    """显示已保存模型选择界面"""
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
    """显示预测执行界面"""
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
    """显示预测结果"""
    if st.session_state.predictions is not None:
        st.markdown("## 预测结果")

        with st.container(border=True):
            # 预测分布图
            st.markdown("### 预测分布")
            fig = create_prediction_distribution_plot(
                st.session_state.predictions, st.session_state.predictor.problem_type
            )
            st.plotly_chart(fig, use_container_width=True)

            # 预测结果预览
            st.markdown("### 预测结果预览")
            original_data = st.session_state.uploaded_data.copy()
            if st.session_state.predictor.problem_type == "classification":
                original_data["预测类别"] = st.session_state.predictions
                original_data["预测概率"] = st.session_state.probabilities[:, 1]
            else:
                original_data["预测值"] = st.session_state.predictions

            st.dataframe(original_data, use_container_width=True)

            # 提供下载预测结果的选项
            csv = original_data.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 下载预测结果",
                data=csv,
                file_name="prediction_results.csv",
                mime="text/csv",
            )
