import streamlit as st
import os
import uuid
from typing import List, Union
import asyncio
import sys
import pandas as pd

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.resume_management.storage.resume_storage_handler import (
    save_pdf_to_minio,
    calculate_file_hash,
    extract_text_from_url,
    calculate_url_hash,
    extract_text_from_pdf,
)
from backend.resume_management.storage.resume_db_operations import (
    store_resume_record,
    get_resume_by_hash,
)
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.query_params.role = st.session_state.role

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


def main():
    st.title("📤 简历上传系统")
    st.markdown("---")

    display_info_message()
    display_workflow()

    with st.container(border=True):
        tab1, tab2 = st.tabs(["PDF上传", "URL输入"])

        with tab1:
            handle_pdf_upload()

        with tab2:
            handle_url_input()

    # 显示页脚
    show_footer()


def display_info_message():
    st.info(
        """
        智能简历上传系统支持PDF文件上传和URL输入两种方式。
        系统会自动提取简历内容,并进行去重和存储。
        上传的简历将用于后续的智能匹配和分析。
        """
    )


def display_workflow():
    with st.expander("📄 查看简历上传工作流程", expanded=False):
        st.markdown(
            """
            1. **文件上传/URL输入**: 选择上传PDF文件或输入简历URL。
            2. **内容提取**: 系统自动提取简历内容。
            3. **去重检查**: 检查是否存在重复简历。
            4. **数据存储**: 将新的简历信息存储到数据库。
            5. **确认反馈**: 向用户显示上传/处理结果。
            """
        )


def handle_pdf_upload():
    with st.container(border=True):
        uploaded_files = st.file_uploader(
            "上传PDF简历", type=["pdf"], accept_multiple_files=True
        )

        if uploaded_files:
            if st.button("开始处理上传的PDF文件"):
                results = []
                for file in uploaded_files:
                    result = process_pdf_file(file)
                    results.append(result)
                display_upload_results(results)


def process_pdf_file(file):
    file_hash = calculate_file_hash(file)
    existing_resume = get_resume_by_hash(file_hash)

    if existing_resume:
        return {
            "file_name": file.name,
            "status": "已存在",
            "message": "文件已存在于数据库中",
        }
    else:
        try:
            minio_path = save_pdf_to_minio(file)
            raw_content = extract_text_from_pdf(file)
            store_resume_record(
                file_hash, "pdf", file.name, None, minio_path, raw_content
            )
            return {
                "file_name": file.name,
                "status": "成功",
                "message": "上传成功并保存到数据库",
            }
        except Exception as e:
            return {
                "file_name": file.name,
                "status": "失败",
                "message": f"处理出错: {str(e)}",
            }


def display_upload_results(results):
    df = pd.DataFrame(results)
    st.table(df)

    success_count = sum(1 for result in results if result["status"] == "成功")
    exist_count = sum(1 for result in results if result["status"] == "已存在")
    fail_count = sum(1 for result in results if result["status"] == "失败")

    st.markdown(
        f"**处理总结:** 成功上传 {success_count} 个文件, {exist_count} 个文件已存在, {fail_count} 个文件处理失败"
    )


def handle_url_input():
    with st.container(border=True):
        url = st.text_input("输入简历URL")

        if url and st.button("提交URL"):
            asyncio.run(process_url(url))


async def process_url(url: str):
    with st.spinner("正在处理URL..."):
        try:
            logger.info(f"开始处理URL: {url}")
            content = await extract_text_from_url(url)
            url_hash = calculate_url_hash(content)

            logger.info(f"URL内容提取成功，哈希值: {url_hash}")

            existing_resume = get_resume_by_hash(url_hash)

            if existing_resume:
                st.warning("此URL的简历内容已存在于数据库中。")
                logger.info(f"URL {url} 的内容已存在于数据库中")
            else:
                store_resume_record(url_hash, "url", None, url, None, content)
                st.success("URL简历已成功保存到数据库。")
                logger.info(f"URL {url} 的简历信息已成功保存到数据库")
        except Exception as e:
            logger.error(f"处理URL时出错: {str(e)}", exc_info=True)
            st.error(f"处理URL时出错: {str(e)}")


main()
