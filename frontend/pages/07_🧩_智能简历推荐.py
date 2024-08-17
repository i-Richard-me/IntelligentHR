import streamlit as st
import sys
import os
import pandas as pd
from PIL import Image

# 获取项目根目录的绝对路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# 将项目根目录添加到 sys.path
sys.path.append(project_root)

from backend.resume_management.recommendation.resume_recommender import (
    ResumeRecommender,
)
from frontend.ui_components import show_sidebar, show_footer, apply_common_styles

# 设置页面配置
st.set_page_config(page_title="智能HR助手 - 简历推荐助手", page_icon="👥")

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()


# 定义节点名称到用户友好描述的映射
def get_node_description(node_name):
    node_descriptions = {
        "generate_search_strategy": "生成简历搜索策略",
        "calculate_resume_scores": "计算总体简历得分",
        "fetch_resume_details": "获取简历详细信息",
        "generate_recommendation_reasons": "生成推荐理由",
        "prepare_final_recommendations": "准备最终输出",
    }
    return node_descriptions.get(node_name, "处理中...")


def display_info_message():
    """
    显示智能简历推荐系统的功能介绍。
    """
    st.info(
        """
    **👥 智能简历推荐系统**

    智能简历推荐系统利用大模型的语义理解能力，实现高效的招聘需求匹配。

    系统能够通过对话式交互，从用户描述中推断出理想候选人画像，并自动生成精准的搜索策略。基于多维度评分机制，系统快速筛选出最匹配的简历，适用于各类人才甄选场景。
    """
    )


def display_workflow():
    """
    显示智能简历推荐系统的工作流程。
    """
    with st.expander("👥 查看简历推荐工作流程", expanded=False):
        st.markdown(
            '<h2 class="section-title">简历推荐工作流程</h2>', unsafe_allow_html=True
        )

        col1, col2 = st.columns([1, 1])

        with col2:
            st.markdown(
                """
                <div class="workflow-container">
                    <div class="workflow-step">
                        <strong>1. 对话式需求分析</strong>: 通过智能对话，深入理解用户的招聘需求，构建理想候选人画像。
                    </div>
                    <div class="workflow-step">
                        <strong>2. 候选人画像生成</strong>: 基于对话内容，自动生成全面的理想候选人特征描述。
                    </div>
                    <div class="workflow-step">
                        <strong>3. 搜索策略制定</strong>: 根据候选人画像，创建精准的简历搜索和匹配策略。
                    </div>
                    <div class="workflow-step">
                        <strong>4. 多维度简历评分</strong>: 利用向量匹配技术，对简历进行全方位的相似度评估。
                    </div>
                    <div class="workflow-step">
                        <strong>5. 结果筛选与排序</strong>: 综合评分结果，筛选并排序最匹配的候选人简历。
                    </div>
                    <div class="workflow-step">
                        <strong>6. 推荐结果展示</strong>: 以清晰、直观的方式呈现推荐结果，支持进一步筛选和分析。
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# 初始化会话状态
if "recommender" not in st.session_state:
    st.session_state.recommender = ResumeRecommender()
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "您好，我是智能简历推荐助手。请告诉我您的招聘需求。",
        }
    ]
    st.session_state.current_stage = "initial_query"
    st.session_state.search_strategy = None
    st.session_state.recommendations = None
    st.session_state.processing = False
    st.session_state.strategy_displayed = False
    st.session_state.refined_query = None
    st.session_state.top_n = 3  # 默认推荐数量

# 主界面
st.title("👥 智能简历推荐系统")
st.markdown("---")

display_info_message()
display_workflow()

st.markdown("---")

st.markdown('<h2 class="section-title">简历推荐</h2>', unsafe_allow_html=True)

# 添加高级设置
with st.expander("高级设置", expanded=False):
    st.session_state.top_n = st.number_input(
        "推荐简历数量", min_value=1, max_value=10, value=st.session_state.top_n
    )

# 创建一个容器来显示聊天历史
chat_container = st.empty()


# 显示聊天历史的函数
def display_chat_history():
    with chat_container.container():
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if isinstance(msg["content"], str):
                    st.write(msg["content"])
                elif isinstance(msg["content"], dict):
                    if "type" in msg["content"]:
                        if msg["content"]["type"] == "search_strategy":
                            st.write("根据您的需求，我们生成了以下检索策略：")
                            st.table(msg["content"]["data"])
                        elif msg["content"]["type"] == "recommendations":
                            st.write("以下是根据您的需求推荐的简历：")
                            for idx, rec in enumerate(msg["content"]["data"], 1):
                                with st.expander(
                                    f"推荐 {idx}: 简历ID {rec['简历ID']} (总分: {rec['总分']:.2f})"
                                ):
                                    st.write(f"个人特征: {rec['个人特征']}")
                                    st.write(f"工作经验: {rec['工作经验']}")
                                    st.write(f"技能概览: {rec['技能概览']}")
                                    st.write(f"推荐理由: {rec['推荐理由']}")


# 初始显示聊天历史
display_chat_history()

# 处理用户输入
if prompt := st.chat_input("输入您的需求或回答"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    display_chat_history()

    if st.session_state.current_stage == "initial_query":
        with st.spinner("正在分析您的需求..."):
            status = st.session_state.recommender.process_query(prompt)
        st.session_state.current_stage = (
            "refining_query"
            if status == "need_more_info"
            else "generating_recommendations"
        )
    elif st.session_state.current_stage == "refining_query":
        with st.spinner("正在处理您的回答..."):
            status = st.session_state.recommender.process_answer(prompt)
        if status == "ready":
            st.session_state.current_stage = "generating_recommendations"

    # 获取系统的下一个问题或推荐结果
    next_question = st.session_state.recommender.get_next_question()
    if next_question:
        st.session_state.messages.append(
            {"role": "assistant", "content": next_question}
        )
        display_chat_history()
    elif st.session_state.current_stage == "generating_recommendations":
        refined_query = st.session_state.recommender.get_refined_query()
        if refined_query:
            st.session_state.refined_query = refined_query
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"根据您的需求，我们总结出以下招聘描述：\n\n{refined_query}",
                }
            )
            display_chat_history()

        st.session_state.processing = True
        st.session_state.strategy_displayed = False

    st.rerun()

# 处理推荐生成过程
if st.session_state.processing:
    with st.spinner("正在生成简历搜索策略..."):
        st.session_state.recommender.generate_search_strategy()

    # 显示检索策略
    collection_relevances = st.session_state.recommender.get_search_strategy()
    if collection_relevances and not st.session_state.strategy_displayed:
        dimension_descriptions = {
            "work_experiences": "工作经历",
            "skills": "专业技能",
            "educations": "教育背景",
            "project_experiences": "项目经验",
            "personal_infos": "个人概况",
        }
        table_data = [
            {
                "维度": dimension_descriptions.get(
                    relevance["collection_name"], relevance["collection_name"]
                ),
                "重要程度": f"{relevance['relevance_score'] * 100:.0f}%",
            }
            for relevance in collection_relevances
        ]
        st.session_state.search_strategy = pd.DataFrame(table_data)

        strategy_message = {
            "type": "search_strategy",
            "data": st.session_state.search_strategy,
        }
        st.session_state.messages.append(
            {"role": "assistant", "content": strategy_message}
        )
        display_chat_history()
        st.session_state.strategy_displayed = True

    with st.spinner("正在生成详细的检索策略..."):
        st.session_state.recommender.generate_detailed_search_strategy()

    with st.spinner("正在计算简历得分..."):
        st.session_state.recommender.calculate_resume_scores(st.session_state.top_n)

    with st.spinner("正在获取简历详细信息..."):
        st.session_state.recommender.resume_details_file = (
            st.session_state.recommender.output_generator.fetch_resume_details(
                st.session_state.recommender.ranked_resume_scores_file
            )
        )

    with st.spinner("正在生成推荐理由..."):
        st.session_state.recommender.generate_recommendation_reasons()

    with st.spinner("正在准备最终推荐结果..."):
        st.session_state.recommender.prepare_final_recommendations()

    st.success("处理完成！")

    # 更新推荐结果
    recommendations = st.session_state.recommender.get_recommendations()
    if recommendations:
        st.session_state.recommendations = recommendations

        recommendation_message = {"type": "recommendations", "data": recommendations}

        st.session_state.messages.append(
            {"role": "assistant", "content": recommendation_message}
        )
        display_chat_history()

        st.info(
            f"以上是为您推荐的 {len(recommendations)} 份简历，您可以展开查看详细信息。如需进行新的查询，请在下方输入框中输入新的需求。"
        )
    else:
        st.warning("抱歉，我们没有找到符合您要求的简历。您可以尝试调整一下需求再试试。")

    st.session_state.current_stage = "initial_query"
    st.session_state.processing = False
    st.session_state.strategy_displayed = False

    st.rerun()

# 页脚
show_footer()
