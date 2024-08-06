import io
import os
import sys
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
from PIL import Image

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from backend.data_processing.table_operation_assistant.table_operation_workflow import (
    DataFrameWorkflow,
)
from frontend.ui_components import show_sidebar, show_footer, apply_common_styles

# 设置页面配置
st.set_page_config(page_title="智能HR助手 - 表格处理助手", page_icon="🧮")

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

# 初始化会话状态
if "workflow" not in st.session_state:
    st.session_state.workflow = DataFrameWorkflow()
if "files_uploaded" not in st.session_state:
    st.session_state.files_uploaded = False


def main():
    """主函数，包含应用的主要逻辑和UI结构。"""
    st.title("🧮 表格处理助手")
    st.markdown("---")

    display_workflow_introduction()
    handle_file_upload()
    if st.session_state.files_uploaded:
        process_user_query()

    show_footer()


def display_workflow_introduction():
    """显示工作流程介绍。"""
    st.markdown(
        '<h2 class="section-title">数据集操作助手工作流程</h2>', unsafe_allow_html=True
    )
    with st.container(border=True):
        col1, col2 = st.columns([1, 1])

        with col1:
            image = Image.open("frontend/assets/dataframe_assistant_workflow.png")
            st.image(image, caption="数据集操作助手流程图", use_column_width=True)

        with col2:
            st.markdown(
                """
            <div class="workflow-container">
                <div class="workflow-step">
                    <strong>1. 多文件上传</strong>: 支持同时上传多个CSV文件。
                </div>
                <div class="workflow-step">
                    <strong>2. 智能对话操作</strong>: 通过AI自然语言交互，理解用户意图并选择数据处理工具。
                </div>
                <div class="workflow-step">
                    <strong>3. 多样化数据操作</strong>: 支持多种数据处理工具，包括但不限于：
                    <ul>
                        <li>表格合并：整合多个数据源</li>
                        <li>数据转置：灵活调整数据结构</li>
                        <li>筛选排序：精确定位所需数据</li>
                        <li>数据集比较：对比两个数据集的差异</li>
                        <li>更多高级操作：满足多样化的数据处理需求</li>
                    </ul>
                </div>
                <div class="workflow-step">
                    <strong>4. 实时结果展示</strong>: 即时显示操作结果，方便用户验证和调整。
                </div>
                <div class="workflow-step">
                    <strong>5. 便捷导出</strong>: 一键下载处理后的数据（Excel格式）。
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )


def handle_file_upload():
    """处理文件上传逻辑。"""
    st.markdown('<h2 class="section-title">数据上传</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        uploaded_files = st.file_uploader(
            "选择CSV文件（可多选）", type="csv", accept_multiple_files=True
        )
        if uploaded_files:
            for uploaded_file in uploaded_files:
                df = pd.read_csv(uploaded_file)
                df_name = uploaded_file.name.split(".")[0]
                st.session_state.workflow.load_dataframe(df_name, df)
                st.success(f"成功加载数据集: {df_name}")

            st.session_state.files_uploaded = True

            display_loaded_dataframes()


def display_loaded_dataframes():
    """显示已加载的数据集信息。"""
    st.markdown("### 已加载的数据集")
    dataframe_info = st.session_state.workflow.get_dataframe_info()
    for name, info in dataframe_info.items():
        with st.expander(f"数据集: {name}"):
            st.write(f"形状: {info['shape']}")
            st.write("列名及数据类型:")
            for col, dtype in info["dtypes"].items():
                st.write(f"  - {col}: {dtype}")


def process_user_query():
    """处理用户查询并显示结果。"""
    st.markdown('<h2 class="section-title">数据集操作</h2>', unsafe_allow_html=True)

    chat_container = st.container(border=True)
    input_placeholder = st.empty()

    display_conversation_history(chat_container)
    user_query = input_placeholder.chat_input("请输入您的数据集操作需求:")

    if user_query:
        display_user_input(chat_container, user_query)
        process_and_display_response(chat_container, user_query)


def display_conversation_history(container):
    """显示对话历史。"""
    with container:
        for message in st.session_state.workflow.conversation_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])


def display_user_input(container, user_query):
    """显示用户输入。"""
    with container:
        with st.chat_message("user"):
            st.markdown(user_query)


def process_and_display_response(container, user_query):
    """处理用户查询并显示响应。"""
    thinking_placeholder = st.empty()

    with thinking_placeholder:
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                result = st.session_state.workflow.process_query(user_query)

    thinking_placeholder.empty()

    display_assistant_response(container, result)


def display_assistant_response(container, result):
    """显示助手的响应。"""
    with container:
        with st.chat_message("assistant"):
            if st.session_state.workflow.current_state == "need_more_info":
                st.markdown(st.session_state.workflow.get_last_message())
            elif st.session_state.workflow.current_state == "ready":
                st.markdown("操作执行成功！")
                display_operation_result(result)
            elif st.session_state.workflow.current_state == "out_of_scope":
                st.markdown(st.session_state.workflow.get_last_message())


def display_operation_result(result):
    """显示操作结果。"""
    if "result_df1" in result and "result_df2" in result:
        display_dual_dataframe_result(result)
    elif "result_df" in result:
        display_single_dataframe_result(result)


def display_dual_dataframe_result(result):
    """显示双数据框结果。"""
    st.subheader("操作结果:")
    tab1, tab2 = st.tabs(["结果1", "结果2"])
    with tab1:
        st.dataframe(result["result_df1"])
    with tab2:
        st.dataframe(result["result_df2"])

    provide_excel_download(result["result_df1"], result["result_df2"])


def display_single_dataframe_result(result):
    """显示单数据框结果。"""
    st.subheader("操作结果:")
    st.dataframe(result["result_df"])

    provide_excel_download(result["result_df"])


def provide_excel_download(*dataframes):
    """提供Excel格式下载选项。"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        for i, df in enumerate(dataframes, 1):
            df.to_excel(writer, sheet_name=f"结果{i}", index=False)
    buffer.seek(0)

    st.download_button(
        label="下载结果Excel",
        data=buffer,
        file_name="operation_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
