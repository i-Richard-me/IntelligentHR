import streamlit as st
import pandas as pd
import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Tuple
import os
import sys

# 获取项目根目录的绝对路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles

# 设置页面配置
st.set_page_config(page_title="智能HR助手 - AI翻译助手", page_icon="🌐")

# 应用自定义样式
apply_common_styles()

# API配置
API_URL = "http://localhost:8765/translation"
MAX_CONCURRENT_REQUESTS = 5
MAX_REQUESTS_PER_MINUTE = 60


async def translate_text(
    session: aiohttp.ClientSession, text: str, text_topic: str
) -> str:
    """
    异步发送翻译请求。

    Args:
        session (aiohttp.ClientSession): 异步HTTP会话。
        text (str): 要翻译的文本。
        text_topic (str): 文本主题。

    Returns:
        str: 翻译后的文本或错误信息。
    """
    try:
        async with session.post(
            API_URL, json={"text": text, "text_topic": text_topic}
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["translated_text"]
            else:
                return f"翻译错误: HTTP {response.status}"
    except Exception as e:
        return f"请求错误: {str(e)}"


async def batch_translate(texts: List[str], text_topic: str) -> List[str]:
    """
    批量翻译文本，包含并发和速率限制。

    Args:
        texts (List[str]): 要翻译的文本列表。
        text_topic (str): 文本主题。

    Returns:
        List[str]: 翻译后的文本列表。
    """
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        tasks = []
        start_time = time.time()

        for i, text in enumerate(texts):
            if i > 0 and i % MAX_REQUESTS_PER_MINUTE == 0:
                elapsed = time.time() - start_time
                if elapsed < 60:
                    await asyncio.sleep(60 - elapsed)
                start_time = time.time()

            async with semaphore:
                task = asyncio.ensure_future(translate_text(session, text, text_topic))
                tasks.append(task)

        return await asyncio.gather(*tasks)


def display_translation_info():
    st.info(
        """
    **🌐 AI翻译助手**

    AI翻译助手是一个高效的多语言翻译工具，专为批量处理文本设计。它支持单条文本和CSV文件的翻译，
    通过上下文理解提高翻译准确性。该工具集成了异步处理和速率限制功能，确保大规模翻译任务的
    稳定性。AI翻译助手适用于需要快速、准确翻译大量文本的各类场景，如国际化文档处理或多语言
    数据分析。
    """
    )


def display_translation_workflow():
    with st.expander("📋 查看AI翻译助手工作流程", expanded=False):
        st.markdown(
            '<h2 class="section-title">AI翻译助手工作流程</h2>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            col1, col2 = st.columns([1, 1])

            # with col1:
            #     st.image(
            #         "frontend/assets/translation_workflow.png",
            #         caption="AI翻译助手流程图",
            #         use_column_width=True,
            #     )

            with col2:
                st.markdown(
                    """
                    **1. 输入准备**
                    指定文本主题，提供上下文信息以提高翻译准确性。

                    **2. 智能翻译**
                    AI模型结合上下文进行翻译，优化专业术语和行业特定表达。

                    **3. 异步处理**
                    系统进行文本分割和批处理，高效处理大量文本。

                    **4. 结果展示**
                    显示翻译结果，支持单条文本即时显示和批量结果预览。
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
    with st.spinner("正在批量翻译..."):
        translated_texts = asyncio.run(batch_translate(texts_to_translate, text_topic))
    df["translated_text"] = translated_texts
    return df


def display_translation_results(translation_results: Any) -> None:
    """
    显示翻译结果。

    Args:
        translation_results (Any): 翻译结果，可能是字典或DataFrame。
    """
    st.markdown('<h2 class="section-title">翻译结果</h2>', unsafe_allow_html=True)
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
    """主函数，包含AI翻译助手的整个流程。"""
    st.title("🌐 AI翻译助手")
    st.markdown("---")

    # 初始化 session state
    if "translation_results" not in st.session_state:
        st.session_state.translation_results = None

    # 显示功能介绍
    display_translation_info()
    st.markdown("---")

    # 显示工作流程
    display_translation_workflow()
    st.markdown("---")

    st.markdown('<h2 class="section-title">文本翻译</h2>', unsafe_allow_html=True)

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
                            batch_translate([text_to_translate], text_topic)
                        )[0]
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


if __name__ == "__main__":
    main()
