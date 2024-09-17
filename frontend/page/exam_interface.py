import streamlit as st
import os
import sys
import asyncio
from typing import List, Dict
import uuid

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from frontend.ui_components import show_sidebar, show_footer, apply_common_styles
from backend.exam_generation.exam_generator import ExamGenerator, ExamQuestion

# st.query_params.role = st.session_state.role

# 应用自定义样式
apply_common_styles()

# 显示侧边栏
show_sidebar()

# 初始化 session state
if "exam_questions" not in st.session_state:
    st.session_state.exam_questions = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "score" not in st.session_state:
    st.session_state.score = None


def main():
    st.title("📝 智能考试系统")
    st.markdown("---")

    display_info_message()

    with st.form("exam_generation_form"):
        text_content = st.text_area("请输入文本材料", height=200)
        submit_button = st.form_submit_button("生成考试题目")

    if submit_button and text_content:
        # 使用 st.spinner 来显示加载状态，并在其中调用异步函数
        with st.spinner("正在生成考试题目..."):
            st.session_state.exam_questions = asyncio.run(
                generate_exam_questions(text_content)
            )
            st.session_state.user_answers = {}
            st.session_state.score = None
        st.rerun()  # 重新运行应用以显示新生成的问题

    if st.session_state.exam_questions:
        display_exam_questions()

    if st.session_state.score is not None:
        display_score()

    show_footer()


def display_info_message():
    st.info(
        """
        智能考试系统可以根据输入的文本材料自动生成考试题目。
        系统会生成5个选择题，每个题目有4个选项。
        完成答题后，系统将自动评分并显示结果。
        """
    )


async def generate_exam_questions(text_content: str) -> List[Dict]:
    generator = ExamGenerator()
    session_id = str(uuid.uuid4())
    questions = await generator.generate_questions(text_content, session_id)
    return questions


def display_exam_questions():
    st.subheader("考试题目")
    with st.form("exam_form"):
        for i, question in enumerate(st.session_state.exam_questions, 1):
            st.write(f"**问题 {i}:** {question['question']}")
            options = question["options"]
            st.session_state.user_answers[i] = st.radio(
                f"选择答案 {i}", options, key=f"q_{i}"
            )
            st.markdown("---")

        submit_exam = st.form_submit_button("提交答案")

    if submit_exam:
        calculate_score()


def calculate_score():
    correct_count = 0
    for i, question in enumerate(st.session_state.exam_questions, 1):
        if st.session_state.user_answers[i] == question["correct_answer"]:
            correct_count += 1

    st.session_state.score = (
        correct_count / len(st.session_state.exam_questions)
    ) * 100


def display_score():
    st.subheader("考试结果")
    st.write(f"您的得分是: {st.session_state.score:.2f}分")

    for i, question in enumerate(st.session_state.exam_questions, 1):
        st.write(f"**问题 {i}:** {question['question']}")
        st.write(f"您的答案: {st.session_state.user_answers[i]}")
        st.write(f"正确答案: {question['correct_answer']}")
        if st.session_state.user_answers[i] == question["correct_answer"]:
            st.success("回答正确！")
        else:
            st.error("回答错误。")
        st.markdown("---")


if __name__ == "__main__":
    main()
