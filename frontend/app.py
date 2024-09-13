import streamlit as st
import sys
import os
from PIL import Image

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

if "role" in st.query_params:
    st.session_state.role = st.query_params.role

if "role" not in st.session_state:
    st.session_state.role = None

ROLES = ["User", "Recruiter", "Admin"]


def login():

    st.title("Intelligent HR Assistant")
    st.header("Log in")
    role = st.selectbox("Choose your role", ROLES)

    if st.button("Log in"):
        st.session_state.role = role
        st.rerun()


def logout():
    st.session_state.role = None
    st.rerun()


role = st.session_state.role

home_page = st.Page("Home.py", title="首页", icon=":material/home:", default=True)
table_operation = st.Page(
    "page/table_operation.py", title="智能数据整理", icon=":material/table_view:"
)
data_cleaning = st.Page(
    "page/data_cleaning.py",
    title="自动化数据清洗",
    icon=":material/mop:",
)
document_check = st.Page(
    "page/document_check.py",
    title="报告质量检验",
    icon=":material/verified:",
)
ai_translation = st.Page(
    "page/ai_translation.py",
    title="智能语境翻译",
    icon=":material/translate:",
)
sentiment_analysis = st.Page(
    "page/sentiment_analysis.py",
    title="情感分析与标注",
    icon=":material/family_star:",
)
text_clustering = st.Page(
    "page/text_clustering.py",
    title="文本聚类分析",
    icon=":material/folder_open:",
)
resume_upload = st.Page(
    "page/resume_upload.py",
    title="简历上传系统",
    icon=":material/upload:",
)
resume_parsing = st.Page(
    "page/resume_parsing.py",
    title="智能简历解析",
    icon=":material/newspaper:",
)
resume_recommendation = st.Page(
    "page/resume_recommendation.py",
    title="智能简历推荐",
    icon=":material/thumb_up:",
)
ai_research = st.Page(
    "page/ai_research.py",
    title="AI研究助手",
    icon=":material/quick_reference_all:",
)
modeling_analysis = st.Page(
    "page/modeling_analysis.py",
    title="建模与分析",
    icon=":material/monitoring:",
)
vector_db_management = st.Page(
    "page/vector_db_management.py",
    title="向量数据库管理",
    icon=":material/database:",
)

account_pages = [home_page]
request_pages = [
    table_operation,
    data_cleaning,
    document_check,
    ai_translation,
    sentiment_analysis,
    text_clustering,
    ai_research,
    modeling_analysis,
]
recruitment_pages = [resume_upload, resume_parsing, resume_recommendation]
admin_pages = [vector_db_management]


# st.logo(
#     "frontend/assets/horizontal_blue.png",
#     icon_image="frontend/assets/icon_blue.png",
# )

# 功能分类
data_processing = [table_operation, data_cleaning, document_check, vector_db_management]

text_analysis = [ai_translation, sentiment_analysis, text_clustering]

talent_management = [resume_upload, resume_parsing, resume_recommendation]

decision_support = [ai_research, modeling_analysis]

# 根据角色分配权限
page_dict = {}
if st.session_state.role in ["User", "Recruiter", "Admin"]:
    page_dict["数据处理与管理"] = [
        p for p in data_processing if p != vector_db_management
    ]
    page_dict["文本分析与洞察"] = text_analysis
    page_dict["辅助决策与研究"] = decision_support

if st.session_state.role in ["Recruiter", "Admin"]:
    page_dict["人才管理工具"] = talent_management

if st.session_state.role == "Admin":
    page_dict["数据处理与管理"].append(vector_db_management)

if len(page_dict) > 0:
    pg = st.navigation({"Account": account_pages} | page_dict)
else:
    pg = st.navigation([st.Page(login)])

pg.run()
