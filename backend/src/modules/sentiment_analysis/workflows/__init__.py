"""
情感分析模块的工作流程
"""
from .sentiment_analysis_workflow import SentimentAnalysisWorkflow
from .sentiment_analysis_result import SentimentAnalysisResult, SentimentAnalysisInput

__all__ = [
    'SentimentAnalysisWorkflow',
    'SentimentAnalysisResult',
    'SentimentAnalysisInput'
]