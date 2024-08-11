"""
本模块包含简历信息提取的核心工作流程。
它定义了从简历文本中提取结构化信息的主要步骤和函数。
"""

from typing import Dict, Any

from backend.resume_management.extractor.resume_data_models import (
    ResumePersonalEducation,
    ResumeWorkProject,
    ResumeSummary,
    CompleteResume,
)
from backend.resume_management.extractor.resume_extraction_prompts import (
    PERSONAL_EDUCATION_SYSTEM_MESSAGE,
    PERSONAL_EDUCATION_HUMAN_MESSAGE,
    WORK_PROJECT_SYSTEM_MESSAGE,
    WORK_PROJECT_HUMAN_MESSAGE,
    RESUME_SUMMARY_SYSTEM_MESSAGE,
    RESUME_SUMMARY_HUMAN_MESSAGE,
)
from utils.llm_tools import LanguageModelChain, init_language_model

# 初始化语言模型
language_model = init_language_model()


def extract_personal_education(resume_content: str) -> Dict[str, Any]:
    """
    从简历内容中提取个人信息和教育背景。

    Args:
        resume_content (str): 简历的文本内容。

    Returns:
        Dict[str, Any]: 包含个人信息和教育背景的字典。
    """
    extractor = LanguageModelChain(
        ResumePersonalEducation,
        PERSONAL_EDUCATION_SYSTEM_MESSAGE,
        PERSONAL_EDUCATION_HUMAN_MESSAGE,
        language_model,
    )
    try:
        result = extractor.invoke({"resume_html": resume_content})
        return result
    except Exception as e:
        raise Exception(f"Error in personal and education extraction: {str(e)}")


def extract_work_project(resume_content: str) -> Dict[str, Any]:
    """
    从简历内容中提取工作和项目经历。

    Args:
        resume_content (str): 简历的文本内容。

    Returns:
        Dict[str, Any]: 包含工作和项目经历的字典。
    """
    extractor = LanguageModelChain(
        ResumeWorkProject,
        WORK_PROJECT_SYSTEM_MESSAGE,
        WORK_PROJECT_HUMAN_MESSAGE,
        language_model,
    )
    try:
        result = extractor.invoke({"resume_html": resume_content})
        return result
    except Exception as e:
        raise Exception(f"Error in work and project extraction: {str(e)}")


def generate_resume_summary(resume_content: str) -> Dict[str, Any]:
    """
    生成简历概述。

    Args:
        resume_content (str): 简历的文本内容。

    Returns:
        Dict[str, Any]: 包含简历概述的字典。
    """
    summarizer = LanguageModelChain(
        ResumeSummary,
        RESUME_SUMMARY_SYSTEM_MESSAGE,
        RESUME_SUMMARY_HUMAN_MESSAGE,
        language_model,
    )
    try:
        result = summarizer.invoke({"resume_html": resume_content})
        return result
    except Exception as e:
        raise Exception(f"Error in summary generation: {str(e)}")


def process_resume(resume_content: str, resume_id: str) -> Dict[str, Any]:
    """
    处理简历，提取所有相关信息并生成完整的简历数据。

    Args:
        resume_content (str): 简历的文本内容。
        resume_id (str): 简历的唯一标识符。

    Returns:
        Dict[str, Any]: 包含完整简历信息的字典。
    """
    try:
        # 提取个人信息和教育背景
        personal_education = extract_personal_education(resume_content)

        # 提取工作和项目经历
        work_project = extract_work_project(resume_content)

        # 生成简历概述
        summary = generate_resume_summary(resume_content)

        # 组合所有信息
        complete_resume = CompleteResume(
            id=resume_id,
            personal_info=personal_education.get("personal_info", {}),
            education=personal_education.get("education", []),
            work_experiences=work_project.get("work_experiences", []),
            project_experiences=work_project.get("project_experiences", []),
            summary=summary,
        )

        return complete_resume.dict()
    except Exception as e:
        return {"error": str(e)}
