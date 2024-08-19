from typing import Dict, Any, List, Optional
from uuid import uuid4
from langfuse.callback import CallbackHandler

from backend.data_processing.data_cleaning.search_tools import SearchTools
from backend.data_processing.data_cleaning.verification_models import (
    input_validator,
    search_analysis,
    name_verifier,
)


def create_langfuse_handler(session_id: str, step: str) -> CallbackHandler:
    """
    创建 Langfuse CallbackHandler。

    Args:
        session_id (str): 会话ID。
        step (str): 当前步骤名称。

    Returns:
        CallbackHandler: Langfuse 回调处理器。
    """
    return CallbackHandler(
        tags=["entity_verification"], session_id=session_id, metadata={"step": step}
    )


class EntityVerificationWorkflow:
    """
    实体验证工作流程类，用于处理和验证实体名称。
    """

    def __init__(self, retriever, entity_type: str, validation_instructions: str, analysis_instructions: str, verification_instructions: str):
        """
        初始化实体验证工作流程。

        Args:
            retriever: 用于检索实体信息的检索器。
            entity_type (str): 实体类型（如"公司名称"、"学校名称"等）。
            validation_instructions (str): 输入验证的补充说明。
            analysis_instructions (str): 搜索结果分析的补充说明。
            verification_instructions (str): 实体验证的补充说明。
        """
        self.retriever = retriever
        self.entity_type = entity_type
        self.validation_instructions = validation_instructions
        self.analysis_instructions = analysis_instructions
        self.verification_instructions = verification_instructions
        self.search_tools = SearchTools()

    def run(self, user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        执行完整的实体验证工作流程。

        Args:
            user_query (str): 用户输入的实体名称查询。
            session_id (Optional[str]): 会话ID，用于跟踪整个工作流程。

        Returns:
            Dict[str, Any]: 包含验证结果的字典。
        """
        if session_id is None:
            session_id = str(uuid4())

        result = self._initialize_result()

        # 步骤1: 验证输入
        langfuse_handler = create_langfuse_handler(session_id, "input_validation")
        result["is_valid"] = self._validate_input(user_query, langfuse_handler)
        if not result["is_valid"]:
            return self._generate_output(result, user_query)

        # 步骤2和3: 网络搜索和分析搜索结果
        search_results = self._perform_web_search(user_query)
        langfuse_handler = create_langfuse_handler(session_id, "search_analysis")
        identified_entity, recognition_status = self._analyze_search_results(
            user_query, search_results, langfuse_handler
        )
        result["identified_entity_name"] = identified_entity
        result["recognition_status"] = recognition_status

        if recognition_status == "known":
            # 步骤4和5: 直接检索和评估名称匹配
            retrieval_results = self._direct_retrieve(identified_entity or user_query)
            result["retrieved_entity_name"] = retrieval_results[0].page_content
            langfuse_handler = create_langfuse_handler(session_id, "name_verification")
            result["verification_status"] = self._evaluate_match(
                user_query,
                result["retrieved_entity_name"],
                search_results,
                langfuse_handler,
            )

            if result["verification_status"] == "verified":
                return self._generate_output(result, user_query, retrieval_results)

        # 如果未验证或未知，进行替代搜索
        alternative_results = self._perform_alternative_search(user_query)
        langfuse_handler = create_langfuse_handler(
            session_id, "alternative_search_analysis"
        )
        identified_entity, recognition_status = self._analyze_search_results(
            user_query, alternative_results, langfuse_handler
        )
        result["identified_entity_name"] = identified_entity
        result["recognition_status"] = recognition_status

        if recognition_status == "known":
            retrieval_results = self._direct_retrieve(identified_entity or user_query)
            result["retrieved_entity_name"] = retrieval_results[0].page_content
            langfuse_handler = create_langfuse_handler(
                session_id, "final_name_verification"
            )
            result["verification_status"] = self._evaluate_match(
                user_query,
                result["retrieved_entity_name"],
                alternative_results,
                langfuse_handler,
            )

        return self._generate_output(result, user_query, retrieval_results)

    def _initialize_result(self) -> Dict[str, Any]:
        """初始化结果字典"""
        return {
            "is_valid": False,
            "identified_entity_name": None,
            "recognition_status": "",
            "retrieved_entity_name": "",
            "verification_status": "",
            "final_entity_name": "",
        }

    def _validate_input(
        self, user_query: str, langfuse_handler: CallbackHandler
    ) -> bool:
        """验证用户输入"""
        print(f"---验证用户输入（{self.entity_type}）---")
        validation_result = input_validator.invoke(
            {
                "user_query": user_query,
                "entity_type": self.entity_type,
                "validation_instructions": self.validation_instructions
            },
            config={"callbacks": [langfuse_handler]}
        )
        return validation_result["is_valid"]

    def _perform_web_search(self, user_query: str) -> str:
        """执行网络搜索"""
        print(f"---执行网络搜索（{self.entity_type}）---")
        return self.search_tools.duckduckgo_search(user_query)

    def _analyze_search_results(
        self, user_query: str, search_results: str, langfuse_handler: CallbackHandler
    ) -> tuple[Optional[str], str]:
        """分析搜索结果"""
        print(f"---分析搜索结果（{self.entity_type}）---")
        analysis_result = search_analysis.invoke(
            {
                "user_query": user_query,
                "snippets": search_results,
                "entity_type": self.entity_type,
                "analysis_instructions": self.analysis_instructions
            },
            config={"callbacks": [langfuse_handler]},
        )
        return (
            analysis_result["identified_entity"] if analysis_result["recognition_status"] == "known" else None,
            analysis_result["recognition_status"],
        )

    def _direct_retrieve(self, search_term: str) -> List:
        """直接从检索器中检索实体信息"""
        print(f"---直接检索（{self.entity_type}）---")
        return self.retriever.invoke(search_term)

    def _evaluate_match(
        self,
        user_query: str,
        retrieved_name: str,
        search_results: str,
        langfuse_handler: CallbackHandler,
    ) -> str:
        """评估检索到的实体名称与用户查询的匹配度"""
        print(f"---评估名称匹配（{self.entity_type}）---")
        verified_result = name_verifier.invoke(
            {
                "user_query": user_query,
                "retrieved_name": retrieved_name,
                "search_results": search_results,
                "entity_type": self.entity_type,
                "verification_instructions": self.verification_instructions
            },
            config={"callbacks": [langfuse_handler]},
        )
        return verified_result["verification_status"]

    def _perform_alternative_search(self, user_query: str) -> str:
        """执行替代搜索"""
        print(f"---执行替代搜索（{self.entity_type}）---")
        return self.search_tools.tavily_search(user_query)

    def _generate_output(
        self,
        result: Dict[str, Any],
        user_query: str,
        retrieval_results: Optional[List] = None,
    ) -> Dict[str, Any]:
        """生成最终输出结果"""
        print(f"---生成最终输出（{self.entity_type}）---")
        if (
            result["is_valid"]
            and retrieval_results
            and result["verification_status"] == "verified"
        ):
            result["final_entity_name"] = retrieval_results[0].metadata.get(
                "standard_name",
                retrieval_results[0].page_content
            )
        elif not result["is_valid"]:
            result["final_entity_name"] = "无效输入"
        else:
            result["final_entity_name"] = "未知"
        print(f"---最终{self.entity_type}：{result['final_entity_name']}---")
        return result