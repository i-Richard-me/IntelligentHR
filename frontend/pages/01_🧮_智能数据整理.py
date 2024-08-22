import io
import os
import sys
from typing import Dict, List, Tuple
import uuid

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
st.set_page_config(page_title="智能HR助手 - 智能数据整理", page_icon="🧮")

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
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "operation_steps" not in st.session_state:
    st.session_state.operation_steps = []


def main():
    """主函数，包含应用的主要逻辑和UI结构。"""
    st.title("🧮 智能数据整理")
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
    显示智能数据整理的信息消息。
    """
    st.info(
        """
    智能数据整理工具利用大模型的语义理解能力，通过自然语言交互实现复杂的表格操作，简化数据处理流程。

    系统能够理解并执行用户的自然语言指令，支持表格合并、数据重塑（宽转长、长转宽）和数据集比较等功能，还能够处理需要多个步骤才能完成的复杂数据处理需求。
    
    适用于各类需要灵活处理和分析表格数据的场景，无需编程知识即可完成高级数据操作。
    """
    )


def display_workflow():
    """
    显示智能数据整理的工作流程。
    """
    with st.expander("📋 查看智能数据整理工作流程", expanded=False):
        with st.container(border=True):
            col1, col2 = st.columns([1, 1])

            with col1:
                image = Image.open("frontend/assets/table_operation_workflow.png")
                st.image(image, caption="智能数据整理流程图", use_column_width=True)

            with col2:
                st.markdown(
                    """
                    1. **数据上传**
                        
                        支持CSV和Excel文件上传
                    
                    2. **自然语言指令输入**
                    
                        用户以对话方式输入数据处理需求，支持描述复杂的多步骤操作需求
        
                    3. **智能操作规划与执行**
                    
                        理解用户需求，自动规划所需操作步骤
                        
                        核心功能包括：
                          * 表格合并
                          * 数据重塑（宽转长、长转宽）
                          * 数据集比较
                        
                        支持多步骤复杂操作的顺序执行
        
                    4. **结果预览与导出**
                    
                        实时展示每个处理步骤的结果，支持导出每个处理步骤的结果
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

            st.session_state.files_uploaded = True

        # 在文件上传的 container 中显示数据预览
        if st.session_state.files_uploaded:
            st.markdown("---")
            st.markdown("#### 上传的数据集预览")
            display_loaded_dataframes()


def display_loaded_dataframes():
    """使用标签页显示已加载的原始数据集预览。"""
    original_dataframes = st.session_state.workflow.get_original_dataframe_info()

    if not original_dataframes:
        st.info("还没有上传任何数据集。请先上传数据文件。")
        return

    # 创建标签页
    tabs = st.tabs(list(original_dataframes.keys()))

    # 为每个原始数据集创建一个标签页
    for tab, (name, info) in zip(tabs, original_dataframes.items()):
        with tab:
            df = st.session_state.workflow.get_dataframe(name)

            # 显示数据预览
            st.dataframe(df.head(5), use_container_width=True)

            # 显示简要信息
            st.caption(f"行数: {info['shape'][0]}, 列数: {info['shape'][1]}")


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
            if result["next_step"] == "need_more_info":
                message = result.get("message", "需要更多信息来处理您的请求。")
                st.markdown(message)
                st.session_state.conversation_history.append(
                    {"role": "assistant", "content": message}
                )
            elif result["next_step"] == "execute_operation":
                message = "操作执行成功！以下是执行的步骤：\n"
                st.markdown(message)
                st.session_state.operation_steps = result.get("operation", [])
                for i, step in enumerate(st.session_state.operation_steps, 1):
                    st.markdown(f"步骤 {i}: {step['tool_name']}")
                full_message = (
                    message
                    + "\n"
                    + "\n".join(
                        [
                            f"步骤 {i}: {step['tool_name']}"
                            for i, step in enumerate(
                                st.session_state.operation_steps, 1
                            )
                        ]
                    )
                )
                st.session_state.conversation_history.append(
                    {"role": "assistant", "content": full_message}
                )
                st.session_state.operation_result = result
            elif result["next_step"] == "out_of_scope":
                message = result.get("message", "抱歉，您的请求超出了我的处理范围。")
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
            for i, step in enumerate(st.session_state.operation_steps, 1):
                output_df_names = step["output_df_names"]
                for df_name in output_df_names:
                    if df_name in st.session_state.workflow.dataframes:
                        df = st.session_state.workflow.dataframes[df_name]
                        st.markdown(f"#### {df_name}")
                        st.caption(f"*由步骤 {i}: {step['tool_name']} 生成*")
                        st.dataframe(df)
                        provide_csv_download(df, df_name)
                st.markdown("---")


def provide_csv_download(df: pd.DataFrame, df_name: str):
    """为单个DataFrame提供CSV格式下载选项。"""
    csv = df.to_csv(index=False)
    st.download_button(
        label=f"下载 {df_name} (CSV)",
        data=csv,
        file_name=f"{df_name}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
