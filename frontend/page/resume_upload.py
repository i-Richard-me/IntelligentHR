import streamlit as st
import os
import uuid
from typing import List, Union
import asyncio
import sys

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

    # 创建两个标签页：一个用于PDF上传，另一个用于URL输入
    tab1, tab2 = st.tabs(["PDF上传", "URL输入"])

    with tab1:
        handle_pdf_upload()

    with tab2:
        handle_url_input()

    # 显示页脚
    show_footer()


def handle_pdf_upload():
    uploaded_files = st.file_uploader(
        "上传PDF简历", type=["pdf"], accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            process_pdf_file(file)


def process_pdf_file(file):

    file_hash = calculate_file_hash(file)
    existing_resume = get_resume_by_hash(file_hash)

    if existing_resume:
        st.warning(f"文件 {file.name} 已存在于数据库中。")
    else:
        try:
            minio_path = save_pdf_to_minio(file)
            raw_content = extract_text_from_pdf(file)
            store_resume_record(
                file_hash, "pdf", file.name, None, minio_path, raw_content
            )
            st.success(f"文件 {file.name} 上传成功并保存到数据库。")
        except Exception as e:
            st.error(f"处理文件 {file.name} 时出错: {str(e)}")


def handle_url_input():
    url = st.text_input("输入简历URL")

    if url and st.button("提交"):
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
