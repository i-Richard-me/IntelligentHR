import os
import sys


# 添加项目根目录到 Python 路径
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
sys.path.append(project_root)


from typing import List
from utils.llm_tools import init_language_model, LanguageModelChain
from backend.text_processing.classification.classification_core import (
    ClassificationResult,
    ClassificationInput,
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_HUMAN_PROMPT,
)


class TextClassificationWorkflow:
    """文本分类工作流程类"""

    def __init__(self):
        """初始化文本分类工作流程"""
        self.language_model = init_language_model()
        self.classification_chain = LanguageModelChain(
            ClassificationResult,
            CLASSIFICATION_SYSTEM_PROMPT,
            CLASSIFICATION_HUMAN_PROMPT,
            self.language_model,
        )()

    def classify_text(self, input_data: ClassificationInput) -> ClassificationResult:
        """
        执行文本分类任务

        Args:
            input_data (ClassificationInput): 包含待分类文本、上下文和标签的输入数据

        Returns:
            ClassificationResult: 分类结果，包含有效性、情感倾向、主题和敏感信息标识
        """
        formatted_labels = "\n".join([f"- {label}" for label in input_data.labels])
        result = self.classification_chain.invoke(
            {
                "text": input_data.text,
                "context": input_data.context,
                "labels": formatted_labels,
            }
        )
        return ClassificationResult(**result)

    def batch_classify(
        self, texts: List[str], context: str, labels: List[str]
    ) -> List[ClassificationResult]:
        """
        批量执行文本分类任务

        Args:
            texts (List[str]): 待分类的文本列表
            context (str): 文本的上下文或主题
            labels (List[str]): 预设的分类标签列表

        Returns:
            List[ClassificationResult]: 分类结果列表
        """
        results = []
        for text in texts:
            input_data = ClassificationInput(text=text, context=context, labels=labels)
            result = self.classify_text(input_data)
            results.append(result)
        return results
