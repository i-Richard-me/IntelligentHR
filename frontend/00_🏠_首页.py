import streamlit as st
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

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

    # 页脚
    show_footer()


def display_project_intro():
    st.markdown(
        """
        智能HR助手是一个实验性的人力资源管理工具集，探索AI技术在HR领域的应用。
        本项目致力于提供从数据处理到决策支持的智能化解决方案，提高HR工作效率。
        
        [📚 查看完整文档](https://docs.irichard.wang/intelligenthr/intelligenthr-intro)
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
    st.markdown('<h2 class="section-title">项目特点</h2>', unsafe_allow_html=True)
    st.markdown(
        """
        - **辅助决策**: 提供数据分析和建议，作为人工决策的参考。

        - **效率尝试**: 自动化部分数据处理和研究任务，探索提高工作效率的可能性。

        - **数据洞察**: 利用AI技术，尝试从数据中提取有价值的信息。

        - **用户友好**: 直观的界面设计，便于使用和测试。

        - **实验性质**: 作为一个探索性项目，持续优化和改进功能。
        """
    )


if __name__ == "__main__":
    main()
