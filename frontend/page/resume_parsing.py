import streamlit as st
import sys
import os
import pdfplumber
import io
import json
import requests
from bs4 import BeautifulSoup
from PIL import Image
import uuid
import asyncio
import pandas as pd
import aiohttp
from typing import List

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.resume_management.extractor.resume_extraction_core import (
    process_resume,
    calculate_resume_hash,
    store_resume,
)
from backend.resume_management.storage.resume_sql_storage import get_full_resume

st.query_params.role = st.session_state.role

# 设置最大并发数
MAX_CONCURRENT_TASKS = 1

# 应用自定义样式
apply_common_styles()

show_sidebar()


def clean_html(html_content):
    """清理HTML内容，移除脚本和样式"""
    soup = BeautifulSoup(html_content, "html.parser")
    for script in soup(["script", "style"]):
        script.decompose()
    return str(soup)


def extract_text_from_pdf(pdf_file):
    """从PDF文件中提取文本"""
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


async def extract_text_from_url(url: str, session: aiohttp.ClientSession) -> str:
    """从URL中异步提取文本"""
    jina_url = f"https://r.jina.ai/{url}"
    async with session.get(jina_url, ssl=False) as response:
        if response.status == 200:
            return await response.text()
        else:
            raise Exception(f"无法从URL提取内容: {url}")


async def extract_resume_info(
    file_content, resume_id, file_type, session_id, file_or_url
):
    """提取简历信息"""
    if file_type == "html":
        content = clean_html(file_content)
    elif file_type == "pdf":
        content = extract_text_from_pdf(io.BytesIO(file_content))
    elif file_type == "url":
        content = file_content
    else:
        st.error("不支持的文件类型")
        return None

    return await process_resume(content, resume_id, session_id, file_type, file_or_url)


def display_resume_info(resume_data):
    """显示提取的简历信息"""
    if not resume_data:
        return

    st.markdown("## 提取的简历信息")

    with st.container(border=True):
        # 简历概述
        display_resume_summary(resume_data)

        # 个人信息
        display_personal_info(resume_data.get("personal_info", {}))

        # 教育背景
        display_education(resume_data.get("education", []))

        # 工作经历
        display_work_experience(resume_data.get("work_experiences", []))

        # 项目经历
        display_project_experience(resume_data.get("project_experiences", []))


def display_resume_summary(resume_data):
    """显示简历概述"""
    with st.container(border=True):
        st.markdown("#### 简历概述")
        st.markdown(f"**特点**: {resume_data.get('characteristics', '')}")
        st.markdown(f"**经验**: {resume_data.get('experience_summary', '')}")
        st.markdown(f"**技能概览**: {resume_data.get('skills_overview', '')}")


def display_personal_info(personal_info):
    """显示个人信息"""
    with st.container(border=True):
        st.markdown("#### 个人信息")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**姓名:** {personal_info.get('name', 'N/A')}")
            st.markdown(f"**邮箱:** {personal_info.get('email', 'N/A')}")
        with col2:
            st.markdown(f"**电话:** {personal_info.get('phone', 'N/A')}")
            st.markdown(f"**地址:** {personal_info.get('address', 'N/A')}")
        st.markdown(f"**个人简介:** {personal_info.get('summary', 'N/A')}")
        if personal_info.get("skills"):
            st.markdown("**技能:**")
            st.markdown(", ".join(personal_info["skills"]))


def display_education(education_list):
    """显示教育背景"""
    with st.container(border=True):
        st.markdown("#### 教育背景")
        for edu in education_list:
            st.markdown(f"**{edu['institution']}** - {edu['degree']} in {edu['major']}")
            st.markdown(f"毕业年份: {edu['graduation_year']}")
            st.markdown("---")


def display_work_experience(work_experiences):
    """显示工作经历"""
    with st.container(border=True):
        st.markdown("#### 工作经历")
        for work in work_experiences:
            st.markdown(
                f"**{work['company']}** - {work['position']} ({work['experience_type']})"
            )
            st.markdown(f"{work['start_date']} to {work['end_date']}")
            st.markdown("职责:")
            for resp in work["responsibilities"]:
                st.markdown(f"- {resp}")
            st.markdown("---")


def display_project_experience(project_experiences):
    """显示项目经历"""
    if project_experiences:
        with st.container(border=True):
            st.markdown("#### 项目经历")
            for proj in project_experiences:
                st.markdown(f"**{proj['name']}** - {proj['role']}")
                st.markdown(f"{proj['start_date']} to {proj['end_date']}")
                st.markdown("详情:")
                for detail in proj["details"]:
                    st.markdown(f"- {detail}")
                st.markdown("---")


def display_info_message():
    """显示智能简历解析系统的功能介绍"""
    st.info(
        """
    智能简历解析系统利用大语言模型，实现对多种格式简历的高效解析。
    
    系统能自动提取和结构化关键信息，有效处理非标准化表述，提高解析准确率。也为后续的简历推荐和人才画像等应用提供了更可靠的数据基础。
    """
    )


def display_workflow():
    """显示智能简历解析系统的工作流程"""
    with st.expander("📄 查看智能简历解析工作流程", expanded=False):
        col1, col2 = st.columns([1, 1])
        with col2:
            st.markdown(
                """
                <div class="workflow-container">
                    <div class="workflow-step">
                        <strong>1. 文件处理与内容提取</strong>
                        - 支持HTML和PDF格式的简历文件
                    </div>
                    <div class="workflow-step">
                        <strong>2. 信息解析与结构化</strong>
                        - 利用大语言模型解析简历内容
                        - 提取个人信息、教育背景、工作经历等关键信息
                    </div>
                    <div class="workflow-step">
                        <strong>3. 简历概述生成</strong>
                        - 基于提取的信息自动生成简历概述
                        - 包括员工特点、工作和项目经历、技能概览等
                    </div>
                    <div class="workflow-step">
                        <strong>4. 结果展示</strong>
                        - 以用户友好的方式可视化展示解析结果
                    </div>
                    <div class="workflow-step">
                        <strong>5. 数据存储（可选）</strong>
                        - 将解析后的数据存储到向量数据库中
                        - 为后续的检索和分析提供基础
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


async def process_single_resume(
    url: str,
    session_id: str,
    semaphore: asyncio.Semaphore,
    session: aiohttp.ClientSession,
) -> None:
    """处理单个简历URL"""
    async with semaphore:  # 使用信号量控制并发
        try:
            resume_content = await extract_text_from_url(url, session)
            resume_id = calculate_resume_hash(resume_content)
            existing_resume = get_full_resume(resume_id)

            if existing_resume:
                st.warning(f"URL {url} 的简历已存在，跳过处理。")
            else:
                resume_data = await process_resume(
                    resume_content, resume_id, session_id, "url", url
                )
                resume_data["resume_format"] = "url"
                resume_data["file_or_url"] = url
                store_resume(resume_data)
                st.success(f"成功处理 URL: {url}")
        except Exception as e:
            st.error(f"处理 URL {url} 时出错: {str(e)}")


async def process_batch_resumes(urls: List[str], session_id: str) -> None:
    """异步处理批量简历，控制并发数"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    async with aiohttp.ClientSession() as session:
        tasks = [
            process_single_resume(url, session_id, semaphore, session) for url in urls
        ]
        await asyncio.gather(*tasks)


def main():
    """主函数，包含 Streamlit 应用的主要逻辑"""
    # 初始化 session_state
    if "resume_data" not in st.session_state:
        st.session_state.resume_data = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "is_from_database" not in st.session_state:
        st.session_state.is_from_database = False

    st.title("📄 智能简历解析")
    st.markdown("---")

    display_info_message()
    display_workflow()

    st.markdown("## 简历提取")

    tab1, tab2 = st.tabs(["单份简历", "批量解析"])

    with tab1:
        handle_single_resume()

    with tab2:
        handle_batch_resumes()

    if st.session_state.resume_data is not None:
        display_resume_results()

    # 页脚
    show_footer()


def handle_single_resume():
    """处理单份简历上传和URL输入"""
    with st.container(border=True):
        uploaded_file = st.file_uploader("上传简历文件", type=["html", "pdf"])
        url_input = st.text_input("或输入简历URL")

        if uploaded_file is not None:
            process_uploaded_file(uploaded_file)
        elif url_input:
            asyncio.run(process_url_input(url_input))


async def process_url_input(url_input: str):
    """处理输入的URL"""
    async with aiohttp.ClientSession() as session:
        file_content = await extract_text_from_url(url_input, session)
        resume_id = calculate_resume_hash(file_content)
        await handle_resume_processing(resume_id, "url", file_content, url_input)


def process_uploaded_file(uploaded_file):
    """处理上传的文件"""
    file_type = uploaded_file.type.split("/")[-1]
    file_content = uploaded_file.read()
    resume_id = calculate_resume_hash(file_content.decode("utf-8", errors="ignore"))

    handle_resume_processing(resume_id, file_type, file_content, uploaded_file.name)


async def handle_resume_processing(resume_id, file_type, file_content, file_or_url):
    """处理简历提取和存储逻辑"""
    existing_resume = get_full_resume(resume_id)
    if existing_resume:
        st.warning("检测到重复的简历。正在从数据库中获取已解析的信息。")
        st.session_state.resume_data = existing_resume
        st.session_state.is_from_database = True
    else:
        st.session_state.is_from_database = False
        if st.button("提取信息", key=file_type):
            with st.spinner("正在提取简历信息..."):
                resume_data = await extract_resume_info(
                    file_content,
                    resume_id,
                    file_type,
                    st.session_state.session_id,
                    file_or_url,
                )
                resume_data["resume_format"] = file_type
                resume_data["file_or_url"] = file_or_url
                st.session_state.resume_data = resume_data


def handle_batch_resumes():
    """处理批量简历上传"""
    with st.container(border=True):
        batch_file = st.file_uploader("上传包含URL的表格文件", type=["csv", "xlsx"])
        if batch_file is not None:
            if st.button("开始批量处理"):
                df = (
                    pd.read_csv(batch_file)
                    if batch_file.name.endswith(".csv")
                    else pd.read_excel(batch_file)
                )
                urls = df["URL"].tolist()

                progress_bar = st.progress(0)
                status_text = st.empty()

                async def process_with_progress():
                    total = len(urls)
                    completed = 0
                    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
                    async with aiohttp.ClientSession() as session:
                        tasks = [
                            process_single_resume(
                                url, st.session_state.session_id, semaphore, session
                            )
                            for url in urls
                        ]
                        for task in asyncio.as_completed(tasks):
                            await task
                            completed += 1
                            progress = completed / total
                            progress_bar.progress(progress)
                            status_text.text(f"已处理 {completed}/{total} 个URL")

                asyncio.run(process_with_progress())

                status_text.text("批量处理完成!")
                st.success(f"成功处理了 {len(urls)} 个URL的简历。")


def display_resume_results():
    """显示简历解析结果和相关操作"""
    st.markdown("---")

    display_resume_info(st.session_state.resume_data)

    # 提供下载选项
    json_string = json.dumps(st.session_state.resume_data, ensure_ascii=False, indent=2)
    st.download_button(
        label="下载JSON结果",
        data=json_string,
        file_name="resume_extracted_info.json",
        mime="application/json",
    )

    # 只有当简历不是从数据库中检索的时候，才显示"存储简历到数据库"按钮
    if not st.session_state.is_from_database:
        if st.button("存储简历到数据库"):
            with st.spinner("正在存储简历数据..."):
                if store_resume(st.session_state.resume_data):
                    st.success("简历数据已成功存储到数据库")
                else:
                    st.error("存储简历数据时出错，请稍后重试")


main()
