import streamlit as st
import pandas as pd
import asyncio
from typing import List, Dict, Any, Tuple
import os
import sys
import uuid

# 获取项目根目录的绝对路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.text_processing.translation.translator import Translator

st.query_params.role = st.session_state.role

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

# 初始化翻译器
translator = Translator()

# 初始化 session state
if "translation_results" not in st.session_state:
    st.session_state.translation_results = None


async def translate_text(text: str, text_topic: str) -> str:
    """
    异步翻译单个文本。

    Args:
        text (str): 要翻译的文本。
        text_topic (str): 文本主题。

    Returns:
        str: 翻译后的文本或错误信息。
    """
    try:
        session_id = str(uuid.uuid4())
        return await translator.translate(text, text_topic, session_id)
    except Exception as e:
        return f"翻译错误: {str(e)}"


async def batch_translate(
    texts: List[str], text_topic: str, session_id: str
) -> List[str]:
    """
    批量翻译文本。

    Args:
        texts (List[str]): 要翻译的文本列表。
        text_topic (str): 文本主题。
        session_id (str): 用于整个CSV文件的session ID。

    Returns:
        List[str]: 翻译后的文本列表。
    """
    tasks = [translator.translate(text, text_topic, session_id) for text in texts]
    return await asyncio.gather(*tasks)


def display_translation_info():
    st.info(
        """
    智能语境翻译是一个高效的多语言翻译工具，专为批量处理文本设计。它支持单条文本和CSV文件的翻译，
    通过上下文理解提高翻译准确性。该工具利用异步处理功能，确保大规模翻译任务的稳定性。
    智能语境翻译适用于需要快速、准确翻译大量文本的各类场景，如国际化文档处理或多语言数据分析。
    """
    )


def upload_and_process_file() -> Tuple[pd.DataFrame, str]:
    """
    上传并处理CSV文件。

    Returns:
        Tuple[pd.DataFrame, str]: 包含上传的数据框和选中的文本列名。
    """
    uploaded_file = st.file_uploader("上传CSV文件", type="csv")
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("预览上传的数据：")
            st.dataframe(df.head())

            text_column = st.selectbox("选择包含要翻译文本的列", df.columns)
            return df, text_column
        except Exception as e:
            st.error(f"处理CSV文件时出错：{str(e)}")
    return None, None


def perform_translation(
    df: pd.DataFrame, text_column: str, text_topic: str
) -> pd.DataFrame:
    """
    执行批量翻译。

    Args:
        df (pd.DataFrame): 包含要翻译文本的数据框。
        text_column (str): 要翻译的文本列名。
        text_topic (str): 文本主题。

    Returns:
        pd.DataFrame: 包含翻译结果的数据框。
    """
    texts_to_translate = df[text_column].tolist()
    session_id = str(uuid.uuid4())
    with st.spinner("正在批量翻译..."):
        translated_texts = asyncio.run(
            batch_translate(texts_to_translate, text_topic, session_id)
        )
    df["translated_text"] = translated_texts
    return df


def display_translation_results(translation_results: Any) -> None:
    """
    显示翻译结果。

    Args:
        translation_results (Any): 翻译结果，可能是字典或DataFrame。
    """
    st.markdown("## 翻译结果")
    with st.container(border=True):
        if isinstance(translation_results, dict):
            with st.expander("查看翻译结果", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("原文")
                    st.markdown(translation_results["original"])
                with col2:
                    st.subheader("译文")
                    st.markdown(translation_results["translated"])
        elif isinstance(translation_results, pd.DataFrame):
            st.dataframe(translation_results)
            csv = translation_results.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="下载翻译结果CSV",
                data=csv,
                file_name="translated_results.csv",
                mime="text/csv",
            )


def main():
    """主函数，包含智能语境翻译的整个流程。"""
    st.title("🌐 智能语境翻译")
    st.markdown("---")

    # 显示功能介绍
    display_translation_info()
    st.markdown("---")

    st.markdown("## 文本翻译")

    with st.container(border=True):
        text_topic = st.text_input(
            "请输入文本主题", placeholder="例如：员工反馈、绩效评价、工作报告等"
        )

        tab1, tab2 = st.tabs(["直接输入", "上传CSV文件"])

        with tab1:
            with st.form("single_translation_form", border=False):
                text_to_translate = st.text_area("请输入要翻译的文本", height=150)
                submit_button = st.form_submit_button("翻译")

                if submit_button and text_to_translate and text_topic:
                    with st.spinner("正在翻译..."):
                        translated_text = asyncio.run(
                            translate_text(text_to_translate, text_topic)
                        )
                    st.session_state.translation_results = {
                        "original": text_to_translate,
                        "translated": translated_text,
                    }

        with tab2:
            df, text_column = upload_and_process_file()
            if df is not None and st.button("开始批量翻译") and text_topic:
                st.session_state.translation_results = perform_translation(
                    df, text_column, text_topic
                )

    if st.session_state.translation_results is not None:
        display_translation_results(st.session_state.translation_results)

    # 页脚
    show_footer()


main()
