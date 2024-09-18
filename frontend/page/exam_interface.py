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
from backend.exam_generation.exam_generator import ExamGenerator, merge_questions

st.query_params.role = st.session_state.role

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
if "generation_complete" not in st.session_state:
    st.session_state.generation_complete = False
if "question_type" not in st.session_state:
    st.session_state.question_type = "选择题"


def main():
    st.title("📝 智能考试系统")
    st.markdown("---")

    display_info_message()

    if not st.session_state.generation_complete:
        with st.form("exam_generation_form"):
            text_content = st.text_area("请输入文本材料", height=200)
            question_type = st.selectbox("选择题型", ["选择题", "判断题"])
            submit_button = st.form_submit_button("生成考试题目")

        if submit_button and text_content:
            st.session_state.question_type = question_type
            with st.spinner("正在生成考试题目..."):
                st.session_state.exam_questions = asyncio.run(
                    generate_exam_questions(text_content, question_type)
                )
                st.session_state.user_answers = {}
                st.session_state.score = None
                st.session_state.generation_complete = True
            st.rerun()
    else:
        display_exam_questions()

    if st.session_state.score is not None:
        display_score()

    show_footer()


def display_info_message():
    st.info(
        """
        智能考试系统可以根据输入的文本材料自动生成考试题目。
        系统会生成10个题目，可以选择生成选择题或判断题。
        完成答题后，系统将自动评分并显示结果。
        """
    )


async def generate_exam_questions(text_content: str, question_type: str) -> List[Dict]:
    generator = ExamGenerator()
    session_id = str(uuid.uuid4())

    # 第一轮生成5个问题
    first_round = await generator.generate_questions(
        text_content, session_id, num_questions=5, question_type=question_type
    )

    # 第二轮生成5个问题，传入第一轮的问题以避免重复
    second_round = await generator.generate_questions(
        text_content,
        session_id,
        num_questions=5,
        question_type=question_type,
        previous_questions=first_round,
    )

    # 合并两轮生成的问题
    all_questions = merge_questions(first_round, second_round)

    # 直接返回合并后的问题列表，因为它们已经是字典格式
    return all_questions


def display_exam_questions():
    st.subheader("考试题目")
    with st.form("exam_form"):
        for i, question in enumerate(st.session_state.exam_questions, 1):
            st.write(f"**问题 {i}:** {question['question']}")
            if st.session_state.question_type == "选择题":
                options = question["options"]
                st.session_state.user_answers[i] = st.radio(
                    f"选择答案 {i}", options, key=f"q_{i}"
                )
            else:  # 判断题
                st.session_state.user_answers[i] = st.radio(
                    f"选择答案 {i}", ["True", "False"], key=f"q_{i}"
                )
            st.markdown("---")

        submit_exam = st.form_submit_button("提交答案")

    if submit_exam:
        calculate_score()


def calculate_score():
    correct_count = 0
    for i, question in enumerate(st.session_state.exam_questions, 1):
        user_answer = st.session_state.user_answers[i]
        correct_answer = question["correct_answer"]

        if st.session_state.question_type == "判断题":
            user_answer = user_answer.lower() == "true"

        if user_answer == correct_answer:
            correct_count += 1

    st.session_state.score = (
        correct_count / len(st.session_state.exam_questions)
    ) * 100


def display_score():
    st.subheader("考试结果")
    st.write(f"您的得分是: {st.session_state.score:.2f}分")

    for i, question in enumerate(st.session_state.exam_questions, 1):
        st.write(f"**问题 {i}:** {question['question']}")
        user_answer = st.session_state.user_answers[i]
        correct_answer = question["correct_answer"]

        if st.session_state.question_type == "选择题":
            st.write(f"您的答案: {user_answer}")
            st.write(f"正确答案: {correct_answer}")
        else:  # 判断题
            st.write(f"您的答案: {'True' if user_answer == 'True' else 'False'}")
            st.write(f"正确答案: {'True' if correct_answer else 'False'}")

        if (
            st.session_state.question_type == "选择题" and user_answer == correct_answer
        ) or (
            st.session_state.question_type == "判断题"
            and user_answer.lower() == str(correct_answer).lower()
        ):
            st.success("回答正确！")
        else:
            st.error("回答错误。")
        st.markdown("---")


main()
