import streamlit as st
import sys
import os
import pdfplumber
import io
import json
from bs4 import BeautifulSoup
from PIL import Image

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.resume_management.extractor.resume_extraction_core import (
    process_resume,
    calculate_resume_hash,
)

# 设置页面配置
st.set_page_config(
    page_title="智能HR助手 - 简历信息提取",
    page_icon="📄",
)

# 应用自定义样式
apply_common_styles()


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


def extract_resume_info(file_content, resume_id, file_type):
    """提取简历信息"""
    if file_type == "html":
        content = clean_html(file_content)
    elif file_type == "pdf":
        content = extract_text_from_pdf(io.BytesIO(file_content))
    else:
        st.error("不支持的文件类型")
        return None

    return process_resume(content, resume_id)


def display_resume_info(resume_data):
    """显示提取的简历信息"""
    if not resume_data:
        return

    st.markdown('<h2 class="section-title">提取的简历信息</h2>', unsafe_allow_html=True)

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


def main():
    """主函数，包含 Streamlit 应用的主要逻辑"""
    # 初始化 session_state
    if "resume_data" not in st.session_state:
        st.session_state.resume_data = None

    st.title("📄 简历信息提取")
    st.markdown("---")

    # 工作流程介绍
    st.markdown(
        '<h2 class="section-title">简历信息提取工作流程</h2>', unsafe_allow_html=True
    )
    with st.container(border=True):
        col1, col2 = st.columns([1, 1])

        # with col1:
        #     image = Image.open("frontend/assets/resume_extraction_workflow.png")
        #     st.image(image, caption="简历信息提取流程图", use_column_width=True)

        with col2:
            st.markdown(
                """
            <div class="workflow-container">
                <div class="workflow-step">
                    <strong>1. 上传简历</strong>: 用户上传HTML或PDF格式的简历文件。
                </div>
                <div class="workflow-step">
                    <strong>2. 预处理</strong>: 清理文件内容，提取纯文本信息。
                </div>
                <div class="workflow-step">
                    <strong>3. AI解析</strong>: 使用AI模型解析简历内容，提取关键信息。
                </div>
                <div class="workflow-step">
                    <strong>4. 结构化数据生成</strong>: 将提取的信息组织成结构化的数据格式。
                </div>
                <div class="workflow-step">
                    <strong>5. 信息展示</strong>: 以用户友好的方式展示提取的简历信息。
                </div>
                <div class="workflow-step">
                    <strong>6. 数据导出</strong>: 提供提取结果的下载选项。
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    st.markdown('<h2 class="section-title">简历提取</h2>', unsafe_allow_html=True)

    with st.container(border=True):
        uploaded_file = st.file_uploader("上传简历文件", type=["html", "pdf"])

        if uploaded_file is not None:
            file_type = uploaded_file.type.split("/")[-1]
            file_content = uploaded_file.read()
            resume_id = calculate_resume_hash(
                file_content.decode("utf-8", errors="ignore")
            )

            if st.button("提取信息"):
                with st.spinner("正在提取简历信息..."):
                    st.session_state.resume_data = extract_resume_info(
                        file_content, resume_id, file_type
                    )

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

    # 页脚
    show_footer()


if __name__ == "__main__":
    # 显示侧边栏
    show_sidebar()
    main()
