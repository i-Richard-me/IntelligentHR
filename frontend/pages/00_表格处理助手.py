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

from backend.data_processing.table_operation.table_operation_workflow import (
    DataFrameWorkflow,
)
from frontend.ui_components import show_sidebar, show_footer, apply_common_styles

# 设置页面配置
st.set_page_config(page_title="智能HR助手 - 数据集处理助手", page_icon="🧮")

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

# 初始化会话状态
if "workflow" not in st.session_state:
    st.session_state.workflow = DataFrameWorkflow()
if "files_uploaded" not in st.session_state:
    st.session_state.files_uploaded = False
if "operation_result" not in st.session_state:
    st.session_state.operation_result = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []


def main():
    """主函数，包含应用的主要逻辑和UI结构。"""
    st.title("🧮 表格处理助手")
    st.markdown("---")

    display_info_message()
    display_workflow()

    handle_file_upload()
    if st.session_state.files_uploaded:
        process_user_query()
        display_operation_result()

    show_footer()


def display_info_message():
    """
    显示表格处理助手的信息消息。
    """
    st.info(
        """
    **🧮 表格处理助手**

    表格处理助手是一个智能化的数据处理工具，利用大模型的语义理解能力，通过自然语言交互实现复杂的表格操作。

    它能够理解并执行用户的自然语言指令，支持表格合并、数据重塑（宽转长、长转宽）和数据集比较等核心功能。同时提供实时结果预览和便捷的导出功能，大大简化了数据处理流程。
    
    适用于各类需要灵活处理和分析表格数据的场景，无需编程知识即可完成高级数据操作。
    """
    )


def display_workflow():
    """
    显示表格处理助手的工作流程。
    """
    with st.expander("📋 查看表格处理助手工作流程", expanded=False):
        st.markdown(
            '<h2 class="section-title">表格处理助手工作流程</h2>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            col1, col2 = st.columns([1, 1])

            # with col1:
            #     image = Image.open("frontend/assets/table_assistant_workflow.png")
            #     st.image(image, caption="表格处理助手流程图", use_column_width=True)

            with col2:
                st.markdown(
                    """
                    **1. 数据上传**
                    支持CSV文件上传，自动识别和处理文件内容。
                    
                    **2. 自然语言指令输入**
                    用户以对话方式输入数据处理需求，系统实时理解和反馈。
        
                    **3. 智能操作执行**
                    基于用户指令，自动选择并执行适当的数据处理工具函数。
                    - 表格合并
                    - 数据重塑（宽转长、长转宽）
                    - 数据集比较
        
                    **4. 结果预览与反馈**
                    实时展示处理结果，支持进一步的修改和优化请求。
        
                    **5. 结果导出**
                    提供Excel格式的导出选项。
                """
                )


def handle_file_upload():
    """处理文件上传逻辑。"""
    st.markdown('<h2 class="section-title">数据上传</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        uploaded_files = st.file_uploader(
            "选择CSV或Excel文件（可多选）",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_extension = uploaded_file.name.split(".")[-1].lower()
                if file_extension == "csv":
                    df = pd.read_csv(uploaded_file)
                elif file_extension in ["xlsx", "xls"]:
                    # 读取Excel文件的所有sheet
                    xls = pd.ExcelFile(uploaded_file)
                    sheet_names = xls.sheet_names
                    if len(sheet_names) > 1:
                        sheet_name = st.selectbox(
                            f"请选择要导入的sheet（{uploaded_file.name}）：",
                            sheet_names,
                        )
                    else:
                        sheet_name = sheet_names[0]
                    df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
                else:
                    st.error(f"不支持的文件格式：{file_extension}")
                    continue

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
        for message in st.session_state.conversation_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])


def display_user_input(container, user_query):
    """显示用户输入并保存到对话历史。"""
    with container:
        with st.chat_message("user"):
            st.markdown(user_query)
    st.session_state.conversation_history.append(
        {"role": "user", "content": user_query}
    )


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
    """显示助手的响应并保存到对话历史。"""
    with container:
        with st.chat_message("assistant"):
            if st.session_state.workflow.current_state == "need_more_info":
                message = st.session_state.workflow.get_last_message()
                st.markdown(message)
                st.session_state.conversation_history.append(
                    {"role": "assistant", "content": message}
                )
            elif st.session_state.workflow.current_state == "ready":
                message = "操作执行成功！"
                st.markdown(message)
                st.session_state.conversation_history.append(
                    {"role": "assistant", "content": message}
                )
                st.session_state.operation_result = result
            elif st.session_state.workflow.current_state == "out_of_scope":
                message = st.session_state.workflow.get_last_message()
                st.markdown(message)
                st.session_state.conversation_history.append(
                    {"role": "assistant", "content": message}
                )


def display_operation_result():
    """显示操作结果。"""
    if st.session_state.operation_result:
        result = st.session_state.operation_result
        st.markdown('<h2 class="section-title">操作结果</h2>', unsafe_allow_html=True)
        with st.container(border=True):
            if "result_df1" in result and "result_df2" in result:
                display_dual_dataframe_result(result)
            elif "result_df" in result:
                display_single_dataframe_result(result)


def display_dual_dataframe_result(result):
    """显示双数据框结果。"""
    tab1, tab2 = st.tabs(["结果1", "结果2"])
    with tab1:
        st.dataframe(result["result_df1"])
    with tab2:
        st.dataframe(result["result_df2"])

    provide_excel_download(result["result_df1"], result["result_df2"])


def display_single_dataframe_result(result):
    """显示单数据框结果。"""
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
