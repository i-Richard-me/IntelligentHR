import os
from typing import List, Optional
from pydantic import BaseModel, Field
from langfuse.callback import CallbackHandler

from utils.llm_tools import init_language_model, LanguageModelChain


# 更新题目的数据模型
class ExamQuestion(BaseModel):
    question: str = Field(..., description="考试题目")
    options: List[str] = Field(..., description="选项列表，包含4个选项")
    correct_answer: str = Field(..., description="正确答案，为选项列表中的一个")


class ExamQuestions(BaseModel):
    questions: List[ExamQuestion] = Field(..., description="考试题目列表")


# 更新系统消息，增加避免重复的指示
SYSTEM_MESSAGE = """
你是一位专业的考试题目生成器。你的任务是根据提供的文本材料生成高质量的选择题。请遵循以下原则：

1. 仔细阅读并理解提供的文本材料。
2. 生成指定数量的选择题，每个问题应该直接基于文本材料的内容。
3. 每个问题应有4个选项，其中只有一个是正确答案。
4. 确保问题难度适中，能够考察学习者对材料的理解程度。
5. 问题应该涵盖材料的不同方面，避免重复。
6. 使用清晰、准确的语言表述问题和选项。
7. 避免生成与之前已生成的问题重复或过于相似的问题。

请严格按照指定的JSON格式输出结果。
"""

# 更新人类消息模板，增加之前生成的问题和新问题数量
HUMAN_MESSAGE_TEMPLATE = """
请根据以下文本材料生成{num_questions}个选择题：

{text_content}

请确保生成的题目直接基于这段文本，并涵盖其中的关键信息。

以下是之前已经生成的问题，请避免生成重复或过于相似的问题(如果之前没有生成过，请忽略)：
{previous_questions}

请生成与这些问题不同的新问题。
"""


class ExamGenerator:
    def __init__(self):
        self.language_model = init_language_model(
            temperature=0.7,
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL"),
        )
        self.exam_chain = LanguageModelChain(
            ExamQuestions, SYSTEM_MESSAGE, HUMAN_MESSAGE_TEMPLATE, self.language_model
        )()

    async def generate_questions(
        self,
        text_content: str,
        session_id: str,
        num_questions: int = 5,
        previous_questions: Optional[List[ExamQuestion]] = None,
    ) -> List[ExamQuestion]:
        langfuse_handler = CallbackHandler(
            tags=["exam_generation"],
            session_id=session_id,
            metadata={"step": "generate_questions"},
        )

        # 准备之前问题的文本表示
        previous_questions_text = ""
        if previous_questions:
            previous_questions_text = "\n".join(
                [
                    f"问题: {q['question']}\n选项: {', '.join(q['options'])}\n正确答案: {q['correct_answer']}\n"
                    for q in previous_questions
                ]
            )

        try:
            result = await self.exam_chain.ainvoke(
                {
                    "text_content": text_content,
                    "num_questions": num_questions,
                    "previous_questions": previous_questions_text,
                },
                config={"callbacks": [langfuse_handler]},
            )
            return result["questions"]
        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            return []


# 添加一个新的函数来合并两轮生成的问题
def merge_questions(
    first_round: List[ExamQuestion], second_round: List[ExamQuestion]
) -> List[ExamQuestion]:
    return first_round + second_round
