import streamlit as st
import pandas as pd
from PIL import Image
import sys
import os
from typing import Dict, Any, List, Optional

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.data_processing.data_cleaning.data_processor import (
    initialize_vector_store,
    get_company_retriever,
)
from backend.data_processing.data_cleaning.verification_workflow import (
    CompanyVerificationWorkflow,
)

# Streamlit 页面配置
st.set_page_config(
    page_title="智能HR助手 - 公司标签清洗",
    page_icon="🏢",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


@st.cache_resource
def initialize_workflow(use_demo: bool) -> CompanyVerificationWorkflow:
    """
    初始化公司验证工作流。

    Args:
        use_demo (bool): 是否使用演示数据。

    Returns:
        CompanyVerificationWorkflow: 初始化后的工作流对象。
    """
    vector_store = initialize_vector_store(use_demo)
    retriever = get_company_retriever(vector_store)
    return CompanyVerificationWorkflow(retriever)


def main():
    st.title("🏢 自动化数据清洗（公司名称）")
    st.markdown("---")

    # 显示功能介绍
    display_info_message()

    # 显示工作流程
    display_workflow()

    use_demo = st.checkbox(
        "使用演示数据",
        value=False,
        help="勾选此项将使用预设的演示数据，否则将使用已存在的数据库数据。",
    )

    # 初始化工作流
    workflow = initialize_workflow(use_demo)

    # 单个公司验证
    single_company_verification(workflow)

    # 批量处理
    batch_processing(workflow)

    # 页脚
    show_footer()


def display_info_message():
    """
    显示自动化数据清洗工具的功能介绍。
    """
    st.info(
        """
    自动化数据清洗工具集成了大语言模型的推理和工具调用能力，实现高效精准的数据标准化。

    系统通过多阶段验证流程，智能识别和验证输入的公司名称，并利用向量检索技术在公司数据库中进行快速匹配。
    适用于需要大规模标准化和验证公司名称的各类数据处理场景。
    """
    )


def display_workflow():
    """
    显示自动化数据清洗工具的工作流程。
    """
    with st.expander("🏢 查看自动化数据清洗工作流程", expanded=False):
        st.markdown(
            '<h2 class="section-title">自动化数据清洗工作流程</h2>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            col1, col2 = st.columns([1, 1])

            # with col1:
            #     image = Image.open("frontend/assets/company_label_cleaning.png")
            #     st.image(image, caption="自动化数据清洗流程图", use_column_width=True)

            with col2:
                st.markdown(
                    """
                    <div class="workflow-container">
                        <div class="workflow-step">
                            <strong>1. 智能数据验证</strong>: 利用大语言模型的自然语言理解能力，智能识别和初步验证输入的公司名称。
                        </div>
                        <div class="workflow-step">
                            <strong>2. 多源网络搜索</strong>: 调用多个搜索引擎API，全面收集公司相关信息，为后续分析提供丰富数据支持。
                        </div>
                        <div class="workflow-step">
                            <strong>3. 大模型推理分析</strong>: 运用大语言模型的推理能力，从搜索结果中提取关键信息，如公司全称、简称、行业等。
                        </div>
                        <div class="workflow-step">
                            <strong>4. 向量检索匹配</strong>: 将处理后的公司信息转化为向量，在预构建的大规模公司向量数据库中进行高效、精准的相似度匹配。
                        </div>
                        <div class="workflow-step">
                            <strong>5. 结果验证与输出</strong>: 大语言模型对多源信息和匹配结果进行综合分析和验证，生成最终的标准化公司名称。
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def single_company_verification(workflow: CompanyVerificationWorkflow):
    """
    处理单个公司名称的标准化。

    Args:
        workflow (CompanyVerificationWorkflow): 公司名称标准化的工作流对象。
    """
    st.markdown(
        '<h2 class="section-title">单个公司名称标准化</h2>', unsafe_allow_html=True
    )
    with st.form(key="single_company_form"):
        company_name = st.text_input("输入公司名称", placeholder="例如：阿里巴巴")
        submit_button = st.form_submit_button("标准化")
        if submit_button and company_name:
            with st.spinner("正在标准化..."):
                result = workflow.run(company_name)
            display_single_result(result)


def display_single_result(result: Dict[str, Any]):
    """
    显示单个公司名称标准化的结果。

    Args:
        result (Dict[str, Any]): 标准化结果字典。
    """
    st.success("数据清洗完成！")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("最终公司简称", result["final_company_name"])
    with col2:
        st.metric("清洗状态", "有效" if result["is_valid"] else "无效")
    with st.expander("查看详细信息"):
        st.json(result)


def batch_processing(workflow: CompanyVerificationWorkflow):
    """
    处理批量公司名称标准化。

    Args:
        workflow (CompanyVerificationWorkflow): 公司名称标准化工作流对象。
    """
    st.markdown('<h2 class="section-title">批量处理</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        uploaded_file = st.file_uploader("上传CSV文件（包含公司名称列）", type="csv")
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write("预览上传的数据：")
            st.dataframe(df.head())
            if st.button("开始批量处理"):
                process_batch(df, workflow)


def process_batch(df: pd.DataFrame, workflow: CompanyVerificationWorkflow):
    """
    处理批量公司数据。

    Args:
        df (pd.DataFrame): 包含公司名称的DataFrame。
        workflow (CompanyVerificationWorkflow): 公司名称标准化工作流对象。
    """
    results = []
    progress_bar = st.progress(0)
    for i, company_name in enumerate(df.iloc[:, 0]):
        with st.spinner(f"正在处理: {company_name}"):
            result = workflow.run(company_name)
            results.append(vars(result))
        progress_bar.progress((i + 1) / len(df))

    result_df = pd.DataFrame(results)
    st.success("批量处理完成！")
    st.dataframe(result_df)

    csv = result_df.to_csv(index=False)
    st.download_button(
        label="📥 下载处理结果",
        data=csv.encode("utf-8-sig"),
        file_name="processed_companies.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
