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

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.resume_management.extractor.resume_extraction_core import (
    process_resume,
    calculate_resume_hash,
    store_resume,
)

st.query_params.role = st.session_state.role

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


def extract_text_from_url(url):
    """从URL中提取文本"""
    jina_url = f'https://r.jina.ai/{url}'
    response = requests.get(jina_url)
    if response.status_code == 200:
        return response.text
    else:
        st.error("无法从URL提取内容")
        return None


async def extract_resume_info(file_content, resume_id, file_type, session_id):
    """提取简历信息"""
    if file_type == "html":
        content = clean_html(file_content)
    elif file_type == "pdf":
        content = extract_text_from_pdf(io.BytesIO(file_content))
    elif file_type == "url":
        content = extract_text_from_url(file_content)
    else:
        st.error("不支持的文件类型")
        return None

    return await process_resume(content, resume_id, session_id)


def display_resume_info(resume_data):
    """显示提取的简历信息"""
    if not resume_data:
        return

    st.markdown("## 提取的简历信息")

    with st.container(border=True):
        # 简历概述
        with st.container(border=True):
            st.markdown("#### 简历概述")
            summary = resume_data.get("summary", {})
            st.markdown(f"**特点**: {summary.get('characteristics', '')}")
            st.markdown(f"**经验**: {summary.get('experience', '')}")
            st.markdown(f"**技能概览**: {summary.get('skills_overview', '')}")

        # 个人信息
        with st.container(border=True):
            st.markdown("#### 个人信息")
            personal_info = resume_data.get("personal_info", {})
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

        # 教育背景
        with st.container(border=True):
            st.markdown("#### 教育背景")
            for edu in resume_data.get("education", []):
                st.markdown(
                    f"**{edu['institution']}** - {edu['degree']} in {edu['major']}"
                )
                st.markdown(f"毕业年份: {edu['graduation_year']}")
                st.markdown("---")

        # 工作经历
        with st.container(border=True):
            st.markdown("#### 工作经历")
            for work in resume_data.get("work_experiences", []):
                st.markdown(f"**{work['company']}** - {work['position']}")
                st.markdown(f"{work['start_date']} to {work['end_date']}")
                st.markdown("职责:")
                for resp in work["responsibilities"]:
                    st.markdown(f"- {resp}")
                st.markdown("---")

        # 项目经历
        if "project_experiences" in resume_data and resume_data["project_experiences"]:
            with st.container(border=True):
                st.markdown("#### 项目经历")
                for proj in resume_data["project_experiences"]:
                    st.markdown(f"**{proj['name']}** - {proj['role']}")
                    st.markdown(f"{proj['start_date']} to {proj['end_date']}")
                    st.markdown("详情:")
                    for detail in proj["details"]:
                        st.markdown(f"- {detail}")
                    st.markdown("---")


def display_info_message():
    """
    显示智能简历解析系统的功能介绍。
    """
    st.info(
        """
    智能简历解析系统利用大语言模型，实现对多种格式简历的高效解析。
    
    系统能自动提取和结构化关键信息，有效处理非标准化表述，提高解析准确率。也为后续的简历推荐和人才画像等应用提供了更可靠的数据基础。
    """
    )


def display_workflow():
    """
    显示智能简历解析系统的工作流程。
    """
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


def main():
    """主函数，包含 Streamlit 应用的主要逻辑"""
    # 初始化 session_state
    if "resume_data" not in st.session_state:
        st.session_state.resume_data = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    st.title("📄 智能简历解析")
    st.markdown("---")

    display_info_message()
    display_workflow()

    st.markdown("## 简历提取")

    with st.container(border=True):
        uploaded_file = st.file_uploader("上传简历文件", type=["html", "pdf"])
        url_input = st.text_input("或输入简历URL")

        if uploaded_file is not None:
            file_type = uploaded_file.type.split("/")[-1]
            file_content = uploaded_file.read()
            resume_id = calculate_resume_hash(
                file_content.decode("utf-8", errors="ignore")
            )

            if st.button("提取信息", key="file"):
                with st.spinner("正在提取简历信息..."):
                    st.session_state.resume_data = asyncio.run(extract_resume_info(
                        file_content, resume_id, file_type, st.session_state.session_id
                    ))
        elif url_input:
            file_type = "url"
            file_content = url_input
            resume_id = calculate_resume_hash(url_input)

            if st.button("提取信息", key="url"):
                with st.spinner("正在提取简历信息..."):
                    st.session_state.resume_data = asyncio.run(extract_resume_info(
                        file_content, resume_id, file_type, st.session_state.session_id
                    ))

    if st.session_state.resume_data is not None:
        st.markdown("---")

        display_resume_info(st.session_state.resume_data)

        # 提供下载选项
        json_string = json.dumps(
            st.session_state.resume_data, ensure_ascii=False, indent=2
        )
        st.download_button(
            label="下载JSON结果",
            data=json_string,
            file_name="resume_extracted_info.json",
            mime="application/json",
        )

        # 添加存储到数据库的按钮
        if st.button("存储简历到数据库"):
            with st.spinner("正在存储简历数据..."):
                if store_resume(st.session_state.resume_data):
                    st.success("简历数据已成功存储到数据库")
                else:
                    st.error("存储简历数据时出错，请稍后重试")

    # 页脚
    show_footer()


main()
