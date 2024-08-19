import streamlit as st
import pandas as pd
import sys
import os
from typing import Dict, Any, List, Optional
from uuid import uuid4

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.data_processing.data_cleaning.data_processor import (
    initialize_vector_store,
    get_entity_retriever,
)
from backend.data_processing.data_cleaning.verification_workflow import (
    EntityVerificationWorkflow,
)

# Streamlit 页面配置
st.set_page_config(
    page_title="智能HR助手 - 数据标准化",
    page_icon="🏢",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

# 初始化会话状态
if "batch_results" not in st.session_state:
    st.session_state.batch_results = None
if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False

# 定义实体类型选项
ENTITY_TYPES = {
    "公司名称": {
        "csv_path": "data/datasets/company.csv",
        "collection_name": "company_data",
        "validation_instructions": """
        请特别注意，有效的公司名称应该是具体的、可识别的企业实体。
        例如，"科技公司"这样的泛称应被视为无效，而"阿里巴巴"则是有效的。
        """,
        "analysis_instructions": """
        在分析搜索结果时，请特别注意识别公司的正式名称、简称、曾用名等。
        需要推断该公司是否是某家知名公司的合同主体变体或其子公司。
        如果是，最终提供的应该是这家更普遍和知名的公司名称。
        例如，如果搜索结果显示"淘宝（中国）软件有限公司"是阿里巴巴集团的子公司，
        那么应该将"阿里巴巴"识别为标准化的公司名称。
        """,
        "verification_instructions": """
        在验证过程中，请考虑公司的各种可能的名称形式，包括全称、简称、品牌名等。
        即使名称表述不同，只要指向同一个母公司或集团，也应视为匹配。
        例如，"阿里巴巴"和"阿里巴巴集团控股有限公司"应该被视为匹配。
        """,
    },
    "学校名称": {
        "csv_path": "data/datasets/school.csv",
        "collection_name": "school_data",
        "validation_instructions": """
        有效的学校名称应该是具体的教育机构名称。
        例如，"大学"这样的泛称应被视为无效，而"北京大学"则是有效的。
        """,
        "analysis_instructions": """
        分析时注意识别学校的官方名称、常用简称等。
        需要考虑学校可能的更名历史和分校情况。
        例如，如果搜索结果显示"清华大学深圳研究生院"，
        应该将"清华大学"识别为标准化的学校名称。
        """,
        "verification_instructions": """
        验证时考虑学校的不同称呼，包括全称、简称、俗称等。
        只要指向同一所学校，即使表述不同也应视为匹配。
        例如，"北大"和"北京大学"应该被视为匹配。
        """,
    },
}


def initialize_workflow(use_demo: bool, entity_type: str) -> EntityVerificationWorkflow:
    """
    初始化实体验证工作流。

    Args:
        use_demo (bool): 是否使用演示数据。
        entity_type (str): 实体类型。

    Returns:
        EntityVerificationWorkflow: 初始化后的工作流对象。
    """
    entity_info = ENTITY_TYPES[entity_type]
    vector_store = initialize_vector_store(
        use_demo, entity_info["csv_path"], entity_info["collection_name"]
    )
    retriever = get_entity_retriever(vector_store)
    return EntityVerificationWorkflow(
        retriever=retriever,
        entity_type=entity_type,
        validation_instructions=entity_info["validation_instructions"],
        analysis_instructions=entity_info["analysis_instructions"],
        verification_instructions=entity_info["verification_instructions"],
    )


def main():
    st.title("🏢 自动化数据标准化")
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

    # 选择实体类型
    entity_type = st.selectbox("选择实体类型", list(ENTITY_TYPES.keys()))

    # 初始化工作流
    workflow = initialize_workflow(use_demo, entity_type)

    # 单个实体验证
    single_entity_verification(workflow, entity_type)

    # 批量处理
    batch_processing(workflow, entity_type)

    # 页脚
    show_footer()


def display_info_message():
    """
    显示自动化数据标准化工具的功能介绍。
    """
    st.info(
        """
    自动化数据标准化工具集成了大语言模型的推理和工具调用能力，实现高效精准的数据标准化。

    系统通过多阶段验证流程，智能识别和验证输入的实体名称，并利用向量检索技术在数据库中进行快速匹配。
    适用于需要大规模标准化和验证各类实体名称的数据处理场景。
    """
    )


def display_workflow():
    """
    显示自动化数据标准化工具的工作流程。
    """
    with st.expander("🏢 查看自动化数据标准化工作流程", expanded=False):
        st.markdown(
            '<h2 class="section-title">自动化数据标准化工作流程</h2>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            col1, col2 = st.columns([1, 1])

            with col2:
                st.markdown(
                    """
                    <div class="workflow-container">
                        <div class="workflow-step">
                            <strong>1. 智能数据验证</strong>: 利用大语言模型的自然语言理解能力，智能识别和初步验证输入的实体名称。
                        </div>
                        <div class="workflow-step">
                            <strong>2. 多源网络搜索</strong>: 调用多个搜索引擎API，全面收集实体相关信息，为后续分析提供丰富数据支持。
                        </div>
                        <div class="workflow-step">
                            <strong>3. 大模型推理分析</strong>: 运用大语言模型的推理能力，从搜索结果中提取关键信息，如实体全称、简称等。
                        </div>
                        <div class="workflow-step">
                            <strong>4. 向量检索匹配</strong>: 将处理后的实体信息转化为向量，在预构建的大规模实体向量数据库中进行高效、精准的相似度匹配。
                        </div>
                        <div class="workflow-step">
                            <strong>5. 结果验证与输出</strong>: 大语言模型对多源信息和匹配结果进行综合分析和验证，生成最终的标准化实体名称。
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def single_entity_verification(workflow: EntityVerificationWorkflow, entity_type: str):
    """
    处理单个实体名称的标准化。

    Args:
        workflow (EntityVerificationWorkflow): 实体名称标准化的工作流对象。
        entity_type (str): 实体类型。
    """
    st.markdown(
        f'<h2 class="section-title">单个{entity_type}标准化</h2>',
        unsafe_allow_html=True,
    )
    with st.form(key="single_entity_form"):
        entity_name = st.text_input(
            f"输入{entity_type}",
            placeholder=f"例如：{'阿里巴巴' if entity_type == '公司名称' else '北京大学'}",
        )
        submit_button = st.form_submit_button("标准化")
        if submit_button and entity_name:
            with st.spinner("正在标准化..."):
                session_id = str(uuid4())
                result = workflow.run(entity_name, session_id=session_id)
            display_single_result(result, entity_type)


def display_single_result(result: Dict[str, Any], entity_type: str):
    """
    显示单个实体名称标准化的结果。

    Args:
        result (Dict[str, Any]): 标准化结果字典。
        entity_type (str): 实体类型。
    """
    st.success("数据标准化完成！")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"最终{entity_type}", result["final_entity_name"])
    with col2:
        st.metric("标准化状态", "有效" if result["is_valid"] else "无效")
    with st.expander("查看详细信息"):
        st.json(result)


def batch_processing(workflow: EntityVerificationWorkflow, entity_type: str):
    """
    处理批量实体名称标准化。

    Args:
        workflow (EntityVerificationWorkflow): 实体名称标准化工作流对象。
        entity_type (str): 实体类型。
    """
    st.markdown(
        f'<h2 class="section-title">批量{entity_type}标准化</h2>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            f"上传CSV文件（包含{entity_type}列）", type="csv"
        )
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write("预览上传的数据：")
            st.dataframe(df.head())
            if st.button("开始批量处理"):
                process_batch(df, workflow, entity_type)

        # 显示处理结果（如果有）
        if (
            st.session_state.processing_complete
            and st.session_state.batch_results is not None
        ):
            st.success("批量处理完成！")
            st.dataframe(st.session_state.batch_results)

            csv = st.session_state.batch_results.to_csv(index=False)
            st.download_button(
                label="📥 下载处理结果",
                data=csv.encode("utf-8-sig"),
                file_name=f"processed_{entity_type.lower().replace(' ', '_')}.csv",
                mime="text/csv",
            )


def process_batch(
    df: pd.DataFrame, workflow: EntityVerificationWorkflow, entity_type: str
):
    """
    处理批量实体数据。

    Args:
        df (pd.DataFrame): 包含实体名称的DataFrame。
        workflow (EntityVerificationWorkflow): 实体名称标准化工作流对象。
        entity_type (str): 实体类型。
    """
    results = []
    progress_bar = st.progress(0)
    for i, entity_name in enumerate(df.iloc[:, 0]):
        with st.spinner(f"正在处理: {entity_name}"):
            session_id = str(uuid4())  # 为每个实体生成新的 session_id
            result = workflow.run(entity_name, session_id=session_id)
            results.append(result)
        progress_bar.progress((i + 1) / len(df))

    result_df = pd.DataFrame(results)

    # 更新会话状态
    st.session_state.batch_results = result_df
    st.session_state.processing_complete = True

    # 刷新页面以显示结果
    st.experimental_rerun()


if __name__ == "__main__":
    main()
