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

ROLES = [None, "Requester", "Responder", "Admin"]


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

logout_page = st.Page(logout, title="Log out", icon=":material/logout:")
home_page = st.Page("00_🏠_首页.py", title="首页", icon=":material/home:", default=True)
table_operation = st.Page(
    "page/01_🧮_智能数据整理.py", title="智能数据整理", icon=":material/table_view:"
)
data_cleaning = st.Page(
    "page/02_🏢_自动化数据清洗.py",
    title="自动化数据清洗",
    icon=":material/mop:",
)
smart_translation = st.Page(
    "page/03_🌐_智能语境翻译.py",
    title="智能语境翻译",
    icon=":material/translate:",
)
sentiment_analysis = st.Page(
    "page/04_😊_情感分析与文本标注.py",
    title="情感分析与文本标注",
    icon=":material/family_star:",
)
text_clustering = st.Page(
    "page/05_🗂️_文本聚类分析.py",
    title="文本聚类分析",
    icon=":material/folder_open:",
)
resume_parsing = st.Page(
    "page/06_📄_智能简历解析.py",
    title="智能简历解析",
    icon=":material/newspaper:",
)
resume_recommendation = st.Page(
    "page/07_🧩_智能简历推荐.py",
    title="智能简历推荐",
    icon=":material/thumb_up:",
)
ai_research = st.Page(
    "page/08_🔍_AI研究助手.py",
    title="AI研究助手",
    icon=":material/quick_reference_all:",
)
modeling_analysis = st.Page(
    "page/10_🤖_建模与分析.py",
    title="建模与分析",
    icon=":material/monitoring:",
)
vector_db_management = st.Page(
    "page/90_🗄_向量数据库管理.py",
    title="向量数据库管理",
    icon=":material/database:",
)

account_pages = [logout_page, home_page]
request_pages = [
    table_operation,
    data_cleaning,
    smart_translation,
    sentiment_analysis,
    text_clustering,
    resume_parsing,
    resume_recommendation,
    ai_research,
    modeling_analysis,
]
admin_pages = [vector_db_management]


# st.logo(
#     "frontend/assets/horizontal_blue.png",
#     icon_image="frontend/assets/icon_blue.png",
# )

page_dict = {}
if st.session_state.role in ["Requester", "Admin"]:
    page_dict["Request"] = request_pages
if st.session_state.role == "Admin":
    page_dict["Admin"] = admin_pages

if len(page_dict) > 0:
    pg = st.navigation({"Account": account_pages} | page_dict)
else:
    pg = st.navigation([st.Page(login)])

pg.run()
