"""
简历信息提取核心逻辑模块。

本模块包含了简历信息提取的主要功能函数，包括个人信息和教育背景提取、
工作和项目经历提取，以及简历概述生成。
"""

from typing import Dict, Any
import hashlib
from utils.llm_tools import LanguageModelChain, init_language_model
from backend.resume_management.extractor.resume_data_models import (
    ResumePersonalEducation,
    ResumeWorkProject,
    ResumeSummary,
    Summary,
)
from backend.resume_management.extractor.resume_extraction_prompts import (
    PERSONAL_EDUCATION_SYSTEM_MESSAGE,
    PERSONAL_EDUCATION_HUMAN_MESSAGE,
    WORK_PROJECT_SYSTEM_MESSAGE,
    WORK_PROJECT_HUMAN_MESSAGE,
    RESUME_SUMMARY_SYSTEM_MESSAGE,
    RESUME_SUMMARY_HUMAN_MESSAGE,
)
from backend.resume_management.storage.resume_vector_storage import (
    store_resume_in_milvus,
)
import logging

# 配置 logging
logging.basicConfig(level=logging.INFO)

# 初始化语言模型
language_model = init_language_model()


def extract_personal_education(resume_content: str) -> Dict[str, Any]:
    """
    提取简历中的个人信息和教育背景。

    Args:
        resume_content (str): 简历内容文本。

    Returns:
        Dict[str, Any]: 包含个人信息和教育背景的字典。
    """
    extractor = LanguageModelChain(
        ResumePersonalEducation,
        PERSONAL_EDUCATION_SYSTEM_MESSAGE,
        PERSONAL_EDUCATION_HUMAN_MESSAGE,
        language_model,
    )()
    return extractor.invoke({"raw_resume_content": resume_content})


def extract_work_project(resume_content: str) -> Dict[str, Any]:
    """
    提取简历中的工作经历和项目经历。

    Args:
        resume_content (str): 简历内容文本。

    Returns:
        Dict[str, Any]: 包含工作经历和项目经历的字典。
    """
    extractor = LanguageModelChain(
        ResumeWorkProject,
        WORK_PROJECT_SYSTEM_MESSAGE,
        WORK_PROJECT_HUMAN_MESSAGE,
        language_model,
    )()
    return extractor.invoke({"raw_resume_content": resume_content})


def generate_resume_summary(resume_content: str) -> Dict[str, Any]:
    """
    生成简历概述。

    Args:
        resume_content (str): 简历内容文本。

    Returns:
        Dict[str, Any]: 包含简历概述的字典。
    """
    summarizer = LanguageModelChain(
        Summary,
        RESUME_SUMMARY_SYSTEM_MESSAGE,
        RESUME_SUMMARY_HUMAN_MESSAGE,
        language_model,
    )()
    return summarizer.invoke({"raw_resume_content": resume_content})


def process_resume(resume_content: str, resume_id: str) -> Dict[str, Any]:
    """
    处理简历并提取所有相关信息。

    Args:
        resume_content (str): 简历内容文本。
        resume_id (str): 简历的唯一标识符。

    Returns:
        Dict[str, Any]: 包含完整简历信息的字典。
    """
    try:
        personal_education = extract_personal_education(resume_content)
        work_project = extract_work_project(resume_content)
        summary = generate_resume_summary(resume_content)

        # 添加 logging 以展示变量结果
        logging.info(f"个人信息和教育背景: {personal_education}")
        logging.info(f"工作经历和项目经历: {work_project}")
        logging.info(f"简历概述: {summary}")


        complete_resume = {
            "id": resume_id,
            "personal_info": personal_education.get("personal_info") or personal_education.get("PersonalInfo"),
            "education": personal_education.get("education") or personal_education.get("Education"),
            "work_experiences": work_project["work_experiences"] or work_project.get("WorkExperience"),
            "project_experiences": work_project.get("project_experiences", []) or work_project.get("ProjectExperience", []),
            "summary": summary.get("summary", {}) or summary.get("Summary", {}),
        }

        return complete_resume
    except Exception as e:
        return {"error": f"处理简历时出错: {str(e)}"}


def calculate_resume_hash(resume_content: str) -> str:
    """
    计算简历内容的哈希值。

    Args:
        resume_content (str): 简历内容文本。

    Returns:
        str: 简历内容的MD5哈希值。
    """
    return hashlib.md5(resume_content.encode()).hexdigest()


def store_resume(resume_data: Dict[str, Any]) -> bool:
    """
    将处理后的简历数据存储到Milvus数据库中。

    Args:
        resume_data (Dict[str, Any]): 处理后的简历数据。

    Returns:
        bool: 存储操作是否成功。
    """
    try:
        store_resume_in_milvus(resume_data)
        return True
    except Exception as e:
        print(f"存储简历数据时出错: {str(e)}")
        return False
