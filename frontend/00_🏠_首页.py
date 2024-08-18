import streamlit as st
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

set_llm_cache(SQLiteCache(database_path="data/langchain.db"))

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles

# 设置页面配置
st.set_page_config(
    page_title="智能HR助手 - 首页",
    page_icon="🏠",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


def main():
    st.title("🚀 智能HR助手")
    st.markdown("---")

    display_project_intro()
    display_feature_overview()
    display_project_highlights()
    display_documentation_link()

    # 页脚
    show_footer()


def display_project_intro():
    st.markdown(
        """
        智能HR助手是一个实验性的人力资源管理工具集，旨在探索AI技术在HR领域的应用潜力。
        工具集涵盖了从数据处理、文本分析到决策支持的多个HR工作分析环节，致力于为人力资源管理提供全方位的智能化解决方案。
        """
    )


def display_feature_overview():
    st.markdown('<h2 class="section-title">功能概览</h2>', unsafe_allow_html=True)

    features = [
        ("🧮 智能数据整理", "以自然语言交互实现表格数据的智能化处理"),
        ("🏢 自动化数据清洗", "智能处理和标准化公司名称数据"),
        ("🌐 语境数据集翻译", "高效处理大规模多语言数据集"),
        ("😊 情感分析与文本标注", "AI驱动的文本分类、情感分析和自动标注"),
        ("🗂️ 文本聚类分析", "自动发现大量文本数据中的隐藏模式和主题"),
        ("📄 智能简历解析", "自动从简历中提取结构化信息"),
        ("🧩 智能简历推荐", "基于AI的简历匹配和推荐系统"),
        ("🔍 AI研究助手", "生成关于AI驱动的研究报告"),
        ("📊 驱动因素分析", "识别和量化影响关键HR指标的因素"),
    ]

    cols = st.columns(2)
    for i, (icon, desc) in enumerate(features):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"##### {icon}")
                st.markdown(desc)


def display_project_highlights():
    st.markdown('<h2 class="section-title">项目亮点</h2>', unsafe_allow_html=True)
    st.markdown(
        """
        - **实际场景应用**: 将大模型能力融入HR实际工作流程，解决真实痛点
        - **效率提升**: 自动化处理费时费力的重复性工作，显著提高效率
        - **智能分析**: 提供新颖的数据分析视角，助力数据驱动决策
        - **灵活适应**: 针对不同HR任务定制AI解决方案，满足多样化需求
        """
    )


def display_documentation_link():
    st.markdown('<h2 class="section-title">产品文档</h2>', unsafe_allow_html=True)

    st.markdown("探索完整功能、使用指南和最佳实践")
    st.link_button(
        "📚 查看完整文档",
        "https://docs.irichard.wang/intelligenthr/intelligenthr-intro",
    )


if __name__ == "__main__":
    main()
