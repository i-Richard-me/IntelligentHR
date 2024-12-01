import os
import uuid
from typing import Union
from common.utils.llm_tools import init_language_model, LanguageModelChain
from langfuse.callback import CallbackHandler
from .workflow_constants import SINGLE_LABEL_CLASSIFICATION_SYSTEM_PROMPT, MULTI_LABEL_CLASSIFICATION_SYSTEM_PROMPT, TEXT_CLASSIFICATION_HUMAN_PROMPT
from .text_classification_result import TextClassificationResult, MultiLabelTextClassificationResult, TextClassificationInput


class TextClassificationWorkflow:
    """文本分类工作流程类"""

    def __init__(self):
        """初始化文本分类工作流程"""
        self.language_model = init_language_model(
            provider=os.getenv("SMART_LLM_PROVIDER"),
            model_name=os.getenv("SMART_LLM_MODEL"),
        )
        self.single_label_chain = LanguageModelChain(
            TextClassificationResult,
            SINGLE_LABEL_CLASSIFICATION_SYSTEM_PROMPT,
            TEXT_CLASSIFICATION_HUMAN_PROMPT,
            self.language_model,
        )()
        self.multi_label_chain = LanguageModelChain(
            MultiLabelTextClassificationResult,
            MULTI_LABEL_CLASSIFICATION_SYSTEM_PROMPT,
            TEXT_CLASSIFICATION_HUMAN_PROMPT,
            self.language_model,
        )()

    def classify_text(
        self, input_data: TextClassificationInput, session_id: str = None
    ) -> Union[TextClassificationResult, MultiLabelTextClassificationResult]:
        """执行单个文本分类任务

        Args:
            input_data: 包含待分类文本、上下文和分类规则的输入数据
            session_id: 可选的会话ID

        Returns:
            分类结果，包含对应的类别（单标签或多标签）
        """
        session_id = session_id or str(uuid.uuid4())
        langfuse_handler = create_langfuse_handler(
            session_id, "text_classification")

        chain = self.multi_label_chain if input_data.is_multi_label else self.single_label_chain

        result = chain.invoke(
            {
                "text": input_data.text,
                "context": input_data.context,
                "categories": input_data.categories,
            },
            config={"callbacks": [langfuse_handler]},
        )

        if input_data.is_multi_label:
            return MultiLabelTextClassificationResult(**result)
        return TextClassificationResult(**result)


def create_langfuse_handler(session_id: str, step: str) -> CallbackHandler:
    """创建Langfuse回调处理器

    Args:
        session_id: 会话ID
        step: 处理步骤

    Returns:
        Langfuse回调处理器
    """
    return CallbackHandler(
        tags=["text_classification"],
        session_id=session_id,
        metadata={"step": step},
    )
