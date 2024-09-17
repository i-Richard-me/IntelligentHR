import os
from typing import List
from pydantic import BaseModel, Field
from langfuse.callback import CallbackHandler

from utils.llm_tools import init_language_model, LanguageModelChain


# 定义题目的数据模型
class ExamQuestion(BaseModel):
    question: str = Field(..., description="考试题目")
    options: List[str] = Field(..., description="选项列表，包含4个选项")
    correct_answer: str = Field(..., description="正确答案，为选项列表中的一个")


class ExamQuestions(BaseModel):
    questions: List[ExamQuestion] = Field(..., description="考试题目列表")


# 系统消息
SYSTEM_MESSAGE = """
你是一位专业的考试题目生成器。你的任务是根据提供的文本材料生成高质量的选择题。请遵循以下原则：

1. 仔细阅读并理解提供的文本材料。
2. 生成5个选择题，每个问题应该直接基于文本材料的内容。
3. 每个问题应有4个选项，其中只有一个是正确答案。
4. 确保问题难度适中，能够考察学习者对材料的理解程度。
5. 问题应该涵盖材料的不同方面，避免重复。
6. 使用清晰、准确的语言表述问题和选项。

请严格按照指定的JSON格式输出结果。
"""

# 人类消息模板
HUMAN_MESSAGE_TEMPLATE = """
请根据以下文本材料生成5个选择题：

{text_content}

请确保生成的题目直接基于这段文本，并涵盖其中的关键信息。
"""


class ExamGenerator:
    def __init__(self):
        self.language_model = init_language_model(
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL"),
        )
        self.exam_chain = LanguageModelChain(
            ExamQuestions, SYSTEM_MESSAGE, HUMAN_MESSAGE_TEMPLATE, self.language_model
        )()

    async def generate_questions(
        self, text_content: str, session_id: str
    ) -> List[ExamQuestion]:
        langfuse_handler = CallbackHandler(
            tags=["exam_generation"],
            session_id=session_id,
            metadata={"step": "generate_questions"},
        )

        try:
            result = await self.exam_chain.ainvoke(
                {"text_content": text_content}, config={"callbacks": [langfuse_handler]}
            )
            return result["questions"]
        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            return []
