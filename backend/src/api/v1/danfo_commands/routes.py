from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from pydantic import BaseModel

from api.dependencies.auth import get_user_id
from modules.danfo_commands.workflow.workflow import DanfoCommandWorkflow
from modules.danfo_commands.models.models import AssistantResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/danfo-commands",
    tags=["Danfo.js命令生成"],
    responses={404: {"description": "未找到"}}
)


class CommandRequest(BaseModel):
    """Danfo.js命令生成请求模型"""
    user_input: str
    table_info: Dict[str, Dict[str, Any]]


# 创建工作流实例
workflow = DanfoCommandWorkflow.create()


@router.post(
    "/analyze",
    response_model=AssistantResponse,
    summary="分析表格操作需求并生成Danfo.js命令",
    description="分析用户的表格操作需求，返回相应的Danfo.js命令或请求更多信息"
)
async def analyze_operation(
        request: CommandRequest,
        user_id: str = Depends(get_user_id),
) -> AssistantResponse:
    """分析表格操作需求并生成Danfo.js命令"""
    try:
        if not request.table_info:
            raise HTTPException(
                status_code=400,
                detail="必须提供至少一个表格的信息"
            )

        if not request.user_input.strip():
            raise HTTPException(
                status_code=400,
                detail="用户输入不能为空"
            )

        response = await workflow.process_request(
            user_input=request.user_input,
            dataframe_info=request.table_info
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理Danfo.js命令生成请求失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理请求时发生错误: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查服务是否正常运行"
)
async def health_check(
        user_id: str = Depends(get_user_id)
) -> Dict[str, str]:
    """健康检查端点"""
    return {"status": "healthy"}