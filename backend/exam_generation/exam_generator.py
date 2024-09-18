import os
from typing import List, Optional
from pydantic import BaseModel, Field
from langfuse.callback import CallbackHandler
from typing import Dict

from utils.llm_tools import init_language_model, LanguageModelChain


class MultipleChoiceQuestion(BaseModel):
    question: str = Field(..., description="考试题目")
    options: List[str] = Field(..., description="选项列表，包含4个选项")
    correct_answer: str = Field(..., description="正确答案，为选项列表中的一个")


class TrueFalseQuestion(BaseModel):
    question: str = Field(..., description="考试题目")
    correct_answer: bool = Field(..., description="正确答案，True 或 False")


class MultipleChoiceExam(BaseModel):
    questions: List[MultipleChoiceQuestion] = Field(..., description="选择题列表")


class TrueFalseExam(BaseModel):
    questions: List[TrueFalseQuestion] = Field(..., description="判断题列表")


SYSTEM_MESSAGE_MULTIPLE_CHOICE = """
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

SYSTEM_MESSAGE_TRUE_FALSE = """
你是一位专业的考试题目生成器。你的任务是根据提供的文本材料生成高质量的判断题。请遵循以下原则：

1. 仔细阅读并理解提供的文本材料。
2. 生成指定数量的判断题，每个问题应该直接基于文本材料的内容。
3. 每个问题的答案只能是 True 或 False。
4. 确保问题难度适中，能够考察学习者对材料的理解程度。
5. 问题应该涵盖材料的不同方面，避免重复。
6. 使用清晰、准确的语言表述问题。
7. 避免生成与之前已生成的问题重复或过于相似的问题。
8. 确保生成的判断题有一定的挑战性，不要过于简单或明显。

请严格按照指定的JSON格式输出结果。
"""

HUMAN_MESSAGE_TEMPLATE = """
请根据以下文本材料生成{num_questions}个{question_type}：

```
{text_content}
```

请确保生成的题目直接基于这段文本，并涵盖其中的关键信息。

以下是之前已经生成的问题，请避免生成重复或过于相似的问题(如果之前没有生成过，请忽略)：

```
{previous_questions}
```

请生成与这些问题不同的新问题。
"""


class ExamGenerator:
    def __init__(self):
        self.language_model = init_language_model(
            temperature=0.7,
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL"),
        )
        self.multiple_choice_chain = LanguageModelChain(
            MultipleChoiceExam,
            SYSTEM_MESSAGE_MULTIPLE_CHOICE,
            HUMAN_MESSAGE_TEMPLATE,
            self.language_model,
        )()
        self.true_false_chain = LanguageModelChain(
            TrueFalseExam,
            SYSTEM_MESSAGE_TRUE_FALSE,
            HUMAN_MESSAGE_TEMPLATE,
            self.language_model,
        )()

    async def generate_questions(
        self,
        text_content: str,
        session_id: str,
        num_questions: int = 5,
        question_type: str = "选择题",
        previous_questions: Optional[str] = None,
    ) -> List[Dict]:
        langfuse_handler = CallbackHandler(
            tags=["exam_generation"],
            session_id=session_id,
            metadata={"step": "generate_questions", "question_type": question_type},
        )

        try:
            chain = (
                self.multiple_choice_chain
                if question_type == "选择题"
                else self.true_false_chain
            )
            result = await chain.ainvoke(
                {
                    "text_content": text_content,
                    "num_questions": num_questions,
                    "question_type": question_type,
                    "previous_questions": previous_questions or "",
                },
                config={"callbacks": [langfuse_handler]},
            )
            return result["questions"]
        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            return []

    def _format_previous_questions(
        self,
        previous_questions: Optional[List[MultipleChoiceQuestion | TrueFalseQuestion]],
        question_type: str,
    ) -> str:
        if not previous_questions:
            return ""

        formatted_questions = []
        for q in previous_questions:
            if question_type == "选择题" and isinstance(q, MultipleChoiceQuestion):
                formatted_questions.append(
                    f"问题: {q.question}\n选项: {', '.join(q.options)}\n正确答案: {q.correct_answer}\n"
                )
            elif question_type == "判断题" and isinstance(q, TrueFalseQuestion):
                formatted_questions.append(
                    f"问题: {q.question}\n正确答案: {'True' if q.correct_answer else 'False'}\n"
                )

        return "\n".join(formatted_questions)


def merge_questions(
    first_round: List[MultipleChoiceQuestion] | List[TrueFalseQuestion],
    second_round: List[MultipleChoiceQuestion] | List[TrueFalseQuestion],
) -> List[MultipleChoiceQuestion] | List[TrueFalseQuestion]:
    return first_round + second_round
