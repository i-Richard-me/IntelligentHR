import streamlit as st

# 版本号
VERSION = "0.0.1"


def show_sidebar():
    """
    显示应用程序的侧边栏。
    """
    with st.sidebar:
        _render_sidebar_content()
        _add_version_info()
        _add_reset_button()


def _render_sidebar_content():
    """
    渲染侧边栏的主要内容。
    """
    st.markdown(_get_sidebar_style() + _get_sidebar_content(), unsafe_allow_html=True)
    st.markdown("---")


def _get_sidebar_style():
    """
    返回侧边栏的CSS样式。
    """
    return """
    <style>
    [data-testid="stSidebarNav"] {
        background-image: none;
        padding-top: 0;
        max-height: none;
    }
    [data-testid="stSidebarNav"] > ul {
        max-height: none;
        overflow-y: visible;
    }
    .sidebar-content {
        padding: 1rem 0;
    }
    .sidebar-title {
        color: #4F8BF9;
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .sidebar-subtitle {
        font-size: 0.9rem;
        color: #6c757d;
        margin-bottom: 1rem;
        line-height: 1.6;
    }
    .sidebar-info {
        font-size: 0.85rem;
        margin-bottom: 0.5rem;
    }
    .sidebar-link {
        color: #4F8BF9;
        text-decoration: none;
    }
    .sidebar-link:hover {
        text-decoration: underline;
    }
    </style>
    """


def _get_sidebar_content():
    """
    返回侧边栏的HTML内容。
    """
    return """
    <div class="sidebar-content">
        <h1 class="sidebar-title">🚀 智能HR助手</h1>
        <p class="sidebar-subtitle">
            实验性的人力资源管理工具集，探索AI技术在HR领域的应用潜力，为人力资源管理提供全方位的智能化解决方案。
        </p>
        <p class="sidebar-info">
            <strong>开发者:</strong> Richard Wang<br>
            <strong>联系方式:</strong> <a href="mailto:contact@xmail.ing" class="sidebar-link">contact@xmail.ing</a>
        </p>
        <p class="sidebar-info">
            <a href="https://github.com/i-Richard-me/IntelligentHR" target="_blank" class="sidebar-link">GitHub 项目仓库</a>
        </p>
    </div>
    """


def _add_version_info():
    """
    添加版本信息到侧边栏。
    """
    st.caption(f"Version {VERSION}")


def _add_reset_button():
    """
    添加重置按钮到侧边栏。
    """
    if st.button("重置任务", key="reset_button"):
        st.session_state.clear()
        st.rerun()


def show_footer():
    """
    显示应用程序的页脚。
    """
    st.markdown(_get_footer_style() + _get_footer_content(), unsafe_allow_html=True)


def _get_footer_style():
    """
    返回页脚的CSS样式。
    """
    return """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f0f2f6;
        color: #31333F;
        text-align: center;
        padding: 10px 0;
        font-size: 0.8rem;
    }
    .footer a {
        color: #4F8BF9;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
    </style>
    """


def _get_footer_content():
    """
    返回页脚的HTML内容。
    """
    return """
    <div class="footer">
        <span>© 2024 Richard Wang</span> &nbsp;|&nbsp; 
        <a href="https://github.com/i-Richard-me/IntelligentHR" target="_blank">GitHub</a> &nbsp;|&nbsp; 
        <a href="mailto:contact@xmail.ing">contact@xmail.ing</a>
    </div>
    """


def apply_common_styles():
    """
    应用通用的CSS样式。
    """
    st.markdown(_get_common_styles(), unsafe_allow_html=True)


def _get_common_styles():
    """
    返回通用的CSS样式。
    """
    return """
    <style>
    .stButton>button {
        background-color: #f0f2f6;
        color: #31333F;
        border: 1px solid #d1d5db;
        padding: 0.25rem 1rem;
        font-size: 0.875rem;
        border-radius: 0.375rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #e5e7eb;
        border-color: #9ca3af;
    }
    .stTextInput>div>div>input {
        border-color: #E0E0E0;
    }
    .stProgress > div > div > div > div {
        background-color: #4F8BF9;
    }
    .section-title {
        color: #4F8BF9;
        font-size: 1.8rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #4F8BF9;
        padding-bottom: 0.5rem;
    }
    .workflow-container {
        background-color: rgba(248, 249, 250, 0.05);
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(0, 0, 0, 0.125);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    @media (prefers-color-scheme: dark) {
        .workflow-container {
            background-color: rgba(33, 37, 41, 0.05);
            border-color: rgba(255, 255, 255, 0.125);
        }
    }
    .workflow-step {
        margin-bottom: 1rem;
    }
    </style>
    """
