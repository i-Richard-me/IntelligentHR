import streamlit as st
import pandas as pd
import sys
import os
import uuid

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from backend.text_processing.clustering.clustering_workflow import (
    generate_categories,
    classify_texts,
)
from frontend.ui_components import show_sidebar, show_footer, apply_common_styles

# 设置页面配置
st.set_page_config(
    page_title="智能HR助手 - 文本聚类分析",
    page_icon="🔬",
)

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


def initialize_session_state():
    """
    初始化会话状态变量
    """
    session_vars = [
        "df_preprocessed",
        "categories",
        "df_result",
        "text_column",
        "text_topic",
        "session_id",
        "clustering_params",
    ]
    for var in session_vars:
        if var not in st.session_state:
            st.session_state[var] = None

    # 确保session_id总是有值
    if st.session_state.session_id is None:
        st.session_state.session_id = str(uuid.uuid4())

    # 初始化 clustering_params
    if st.session_state.clustering_params is None:
        st.session_state.clustering_params = {
            "min_categories": 10,
            "max_categories": 15,
            "batch_size": 100,
            "classification_batch_size": 20,
        }


def main():
    """
    主函数，控制页面流程和布局
    """
    initialize_session_state()

    st.title("🔬 文本聚类分析")
    st.markdown("---")

    display_info_message()
    display_workflow_introduction()

    handle_data_input_and_clustering()
    review_clustering_results()
    display_classification_results()

    show_footer()


def display_info_message():
    """
    显示表格处理助手的信息消息。
    """
    st.info(
        """
        **🔬 文本聚类分析工具**

        文本聚类分析工具利用大语言模型的语义理解能力，自动化地从大量文本中识别和归类主要主题。

        工具采用分批处理和多阶段聚类策略，能够高效处理大规模文本数据。支持自定义类别数量范围，并提供交互式的类别审核和编辑功能，让用户能够根据具体需求优化聚类结果。
        
        适用于各类文本内容分析场景，如用户反馈归类、话题趋势分析等。
        """
    )


def display_workflow_introduction():
    with st.expander("📋 查看文本聚类分析工作流程", expanded=False):
        with st.container(border=True):
            st.markdown(
                """
            1. **数据准备与参数设置**

                上传CSV文件，选择文本列，输入主题背景，并设置聚类参数。

            2. **初始聚类与类别优化**

                系统使用大语言模型进行初始文本分类，然后合并和优化类别。

            3. **人工审核与调整**

                展示并允许编辑生成的类别列表，优化类别名称和描述。

            4. **文本分类与结果生成**

                基于确认的类别对所有文本进行分类，生成并展示最终结果。

            5. **结果导出**

                提供分类结果的CSV格式下载选项。
            """
            )


def handle_data_input_and_clustering():
    """
    处理数据输入和初始聚类过程
    """
    st.markdown("## 数据输入和初始聚类")

    with st.container(border=True):
        st.session_state.text_topic = st.text_input(
            "请输入文本主题或背景",
            value=st.session_state.text_topic if st.session_state.text_topic else "",
            placeholder="例如：员工反馈、产品评论、客户意见等",
        )

        uploaded_file = st.file_uploader("上传CSV文件", type="csv")
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write("预览上传的数据：")
            st.write(df.head())
            st.session_state.text_column = st.selectbox("选择包含文本的列", df.columns)

            st.session_state.clustering_params = get_clustering_parameters()

            if st.button("开始初始聚类"):
                with st.spinner("正在进行初始聚类..."):
                    result = generate_categories(
                        df=df,
                        text_column=st.session_state.text_column,
                        text_topic=st.session_state.text_topic,
                        initial_category_count=st.session_state.clustering_params[
                            "max_categories"
                        ],
                        min_categories=st.session_state.clustering_params[
                            "min_categories"
                        ],
                        max_categories=st.session_state.clustering_params[
                            "max_categories"
                        ],
                        batch_size=st.session_state.clustering_params["batch_size"],
                        session_id=st.session_state.session_id,
                    )

                st.success("初始聚类完成！")

                # 保存结果到 session state
                st.session_state.df_preprocessed = result["preprocessed_df"]
                st.session_state.categories = result["categories"]["categories"]

        else:
            st.warning("请上传CSV文件")


def get_clustering_parameters():
    """
    获取聚类参数设置

    Returns:
        dict: 包含聚类参数的字典
    """
    with st.expander("聚类参数设置"):
        min_categories = st.slider(
            "最小类别数量",
            5,
            15,
            st.session_state.clustering_params["min_categories"],
            key="min_categories_slider",
        )
        max_categories = st.slider(
            "最大类别数量",
            min_categories,
            20,
            st.session_state.clustering_params["max_categories"],
            key="max_categories_slider",
        )
        batch_size = st.slider(
            "聚类批处理大小",
            10,
            1000,
            st.session_state.clustering_params["batch_size"],
            key="batch_size_slider",
        )
        classification_batch_size = st.slider(
            "分类批处理大小",
            10,
            100,
            st.session_state.clustering_params["classification_batch_size"],
            key="classification_batch_size_slider",
        )

    return {
        "min_categories": min_categories,
        "max_categories": max_categories,
        "batch_size": batch_size,
        "classification_batch_size": classification_batch_size,
    }


def review_clustering_results():
    """
    审核聚类结果并允许用户修改
    """
    if st.session_state.categories is not None:
        st.markdown("---")
        st.markdown("## 聚类结果审核")

        with st.container(border=True):
            st.markdown("请审核并根据需要修改、添加或删除类别：")

            # 将类别列表转换为DataFrame以便使用st.data_editor
            categories_df = pd.DataFrame(st.session_state.categories)[
                ["name", "description"]
            ]

            # 使用st.data_editor来展示和编辑类别
            edited_df = st.data_editor(
                categories_df,
                num_rows="dynamic",
                column_config={
                    "name": st.column_config.TextColumn(
                        "类别名称",
                        help="简洁明了的类别标签",
                        max_chars=50,
                        required=True,
                    ),
                    "description": st.column_config.TextColumn(
                        "类别描述",
                        help="详细描述该类别的特征及与其他类别的区别",
                        max_chars=200,
                        required=True,
                    ),
                },
            )

            # 将编辑后的DataFrame转换回类别列表
            edited_categories = edited_df.to_dict("records")

            if st.button("确认类别并开始文本分类"):
                with st.spinner("正在进行文本分类..."):
                    df_result = classify_texts(
                        df=st.session_state.df_preprocessed,
                        text_column=st.session_state.text_column,
                        id_column="unique_id",
                        categories={"categories": edited_categories},
                        text_topic=st.session_state.text_topic,
                        session_id=st.session_state.session_id,
                        classification_batch_size=st.session_state.clustering_params[
                            "classification_batch_size"
                        ],
                    )

                st.session_state.df_result = df_result
                st.success("文本分类完成！")


def display_classification_results():
    """
    展示分类结果
    """
    if st.session_state.df_result is not None:
        st.markdown("---")
        st.markdown("## 分类结果展示")

        with st.container(border=True):
            st.dataframe(st.session_state.df_result)

            # 提供下载选项
            csv = st.session_state.df_result.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="下载分类结果CSV",
                data=csv,
                file_name="classification_results.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
