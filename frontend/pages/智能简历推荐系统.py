import streamlit as st
import sys
import os
import pandas as pd
from PIL import Image
from typing import Dict, List, Optional

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


def get_node_description(node_name: str) -> str:
    """
    获取节点的用户友好描述。

    Args:
        node_name (str): 节点名称。

    Returns:
        str: 节点的用户友好描述。
    """
    node_descriptions = {
        "generate_resume_search_strategy": "生成简历搜索策略",
        "generate_collection_search_strategy": "生成集合搜索策略",
        "calculate_overall_resume_scores": "计算总体简历得分",
        "fetch_resume_details": "获取简历详细信息",
        "generate_recommendation_reasons": "生成推荐理由",
        "prepare_final_output": "准备最终输出",
    }
    return node_descriptions.get(node_name, "处理中...")


def initialize_session_state():
    """初始化会话状态"""
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


def display_workflow_intro():
    """显示工作流程介绍"""
    st.markdown(
        '<h2 class="section-title">简历推荐工作流程</h2>', unsafe_allow_html=True
    )
    with st.container(border=True):
        col1, col2 = st.columns([1, 1])

        with col1:
            image = Image.open("frontend/assets/resume_recommendation_workflow.png")
            st.image(image, caption="简历推荐助手流程图", use_column_width=True)

        with col2:
            st.markdown(
                """
            <div class="workflow-container">
                <div class="workflow-step">
                    <strong>1. 需求分析</strong>: 智能分析用户的招聘需求，提取关键信息和要求。
                </div>
                <div class="workflow-step">
                    <strong>2. 搜索策略生成</strong>: 根据需求自动生成针对性的简历搜索策略。
                </div>
                <div class="workflow-step">
                    <strong>3. 简历评分</strong>: 利用向量匹配和机器学习算法对简历进行多维度评分。
                </div>
                <div class="workflow-step">
                    <strong>4. 详细信息获取</strong>: 提取候选简历的详细信息，包括工作经验、技能等。
                </div>
                <div class="workflow-step">
                    <strong>5. 推荐理由生成</strong>: 为每份推荐的简历生成个性化的推荐理由。
                </div>
                <div class="workflow-step">
                    <strong>6. 结果呈现</strong>: 以用户友好的方式展示推荐结果，便于快速决策。
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )


def display_chat_history():
    """显示聊天历史"""
    with st.container():
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if isinstance(msg["content"], str):
                    st.write(msg["content"])
                elif isinstance(msg["content"], dict):
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


def handle_user_input(prompt: str):
    """处理用户输入"""
    st.session_state.messages.append({"role": "user", "content": prompt})
    display_chat_history()

    if st.session_state.current_stage == "initial_query":
        with st.spinner("正在分析您的需求..."):
            st.session_state.recommender.process_query(prompt)
        st.session_state.current_stage = "refining_query"
    elif st.session_state.current_stage == "refining_query":
        with st.spinner("正在处理您的回答..."):
            st.session_state.recommender.process_answer(prompt)

    next_question = st.session_state.recommender.get_next_question()
    if next_question:
        st.session_state.messages.append(
            {"role": "assistant", "content": next_question}
        )
        display_chat_history()
    else:
        st.session_state.current_stage = "generating_recommendations"
        refined_query = st.session_state.recommender.get_refined_query()
        if refined_query:
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


def process_recommendations():
    """处理推荐生成过程"""
    while not st.session_state.recommender.is_process_complete():
        next_node = st.session_state.recommender.get_next_node()
        progress_description = get_node_description(next_node)

        with st.spinner(f"当前进度: {progress_description}"):
            result, _ = st.session_state.recommender.continue_process()

        if not st.session_state.strategy_displayed:
            display_search_strategy()

    st.success("处理完成！")
    display_recommendations()


def display_search_strategy():
    """显示搜索策略"""
    collection_relevances = st.session_state.recommender.get_collection_relevances()
    if collection_relevances:
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


def display_recommendations():
    """显示推荐结果"""
    recommendations = st.session_state.recommender.get_recommendations()
    if recommendations:
        st.session_state.recommendations = recommendations

        recommendation_message = {"type": "recommendations", "data": recommendations}

        st.session_state.messages.append(
            {"role": "assistant", "content": recommendation_message}
        )
        display_chat_history()

        st.info(
            "以上是为您推荐的简历，您可以展开查看详细信息。如需进行新的查询，请在下方输入框中输入新的需求。"
        )
    else:
        st.warning("抱歉，我们没有找到符合您要求的简历。您可以尝试调整一下需求再试试。")

    st.session_state.current_stage = "initial_query"
    st.session_state.processing = False
    st.session_state.strategy_displayed = False

    st.rerun()


def main():
    """主函数"""
    st.title("👥 智能简历推荐系统")
    st.markdown("---")

    initialize_session_state()
    display_workflow_intro()

    st.markdown("---")
    st.markdown('<h2 class="section-title">简历推荐</h2>', unsafe_allow_html=True)

    chat_container = st.empty()
    with chat_container:
        display_chat_history()

    if prompt := st.chat_input("输入您的需求或回答"):
        handle_user_input(prompt)

    if st.session_state.processing:
        process_recommendations()

    show_footer()


if __name__ == "__main__":
    main()
