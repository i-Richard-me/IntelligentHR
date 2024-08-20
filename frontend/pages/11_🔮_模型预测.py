import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.data_processing.analysis.model_predictor import (
    ModelPredictor,
    list_available_models,
)

# Streamlit 页面配置
st.set_page_config(
    page_title="智能HR助手 - 模型预测",
    page_icon="🔮",
    layout="wide",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


# 初始化会话状态
def initialize_session_state():
    if "predictor" not in st.session_state:
        st.session_state.predictor = ModelPredictor()
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = None
    if "predictions" not in st.session_state:
        st.session_state.predictions = None
    if "probabilities" not in st.session_state:
        st.session_state.probabilities = None
    if "data_validated" not in st.session_state:
        st.session_state.data_validated = False


def main():
    initialize_session_state()

    st.title("🔮 模型预测")
    st.markdown("---")

    display_info_message()
    display_model_selection()
    display_data_upload_and_preview()
    display_prediction_execution()
    display_results()

    show_footer()


def display_info_message():
    st.info(
        """
    **🔮 模型预测工具**

    这个工具允许您选择之前训练好的模型，上传新的数据集，并进行预测。

    主要功能包括：
    - 模型选择和信息展示
    - 数据上传和预览
    - 执行预测并查看结果
    - 预测结果可视化和下载
    """
    )


def display_model_selection():
    st.markdown('<h3 class="section-title">模型选择</h3>', unsafe_allow_html=True)
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


def display_data_upload_and_preview():
    st.markdown('<h3 class="section-title">数据上传与预览</h3>', unsafe_allow_html=True)
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "上传预测数据 (CSV 或 Excel 文件)", type=["csv", "xlsx"]
        )
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    data = pd.read_csv(uploaded_file)
                else:
                    data = pd.read_excel(uploaded_file)

                st.session_state.data_validated = False

                if st.session_state.predictor.model is not None:
                    model_features = set(st.session_state.predictor.original_features)
                    data_features = set(data.columns)
                    missing_features = model_features - data_features
                    extra_features = data_features - model_features

                    if missing_features:
                        st.warning(
                            f"⚠️ 上传的数据缺少以下特征：{', '.join(missing_features)}"
                        )
                    else:
                        st.session_state.uploaded_data = data
                        st.session_state.data_validated = True
                        st.success("✅ 数据上传成功！")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("数据行数", data.shape[0])
                        with col2:
                            st.metric("数据列数", data.shape[1])
                        with col3:
                            st.metric(
                                "匹配特征数",
                                len(model_features.intersection(data_features)),
                            )
                        with col4:
                            st.metric("额外特征数", len(extra_features))

                        if extra_features:
                            st.info(f"ℹ️ 额外的特征: {', '.join(extra_features)}")

                        st.subheader("数据预览")
                        st.dataframe(data.head(), use_container_width=True)
                else:
                    st.warning("⚠️ 请先选择一个模型，然后再上传数据。")
            except Exception as e:
                st.error(f"读取文件时出错: {str(e)}")


def display_prediction_execution():
    if st.session_state.data_validated:
        st.markdown('<h3 class="section-title">执行预测</h3>', unsafe_allow_html=True)
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


def display_results():
    if (
        st.session_state.predictions is not None
        and st.session_state.probabilities is not None
    ):
        st.markdown('<h3 class="section-title">预测结果</h3>', unsafe_allow_html=True)
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


if __name__ == "__main__":
    main()
