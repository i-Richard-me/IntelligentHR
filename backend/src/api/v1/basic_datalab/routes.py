from fastapi import APIRouter, HTTPException, Depends
import logging
from api.dependencies.auth import get_user_id
from modules.basic_datalab.workflow.workflow import BasicDatalabWorkflow
from modules.basic_datalab.models.models import AssistantResponse, AnalysisRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/basic-datalab",
    tags=["基础数据工坊"],
    responses={404: {"description": "未找到"}}
)

# 创建工作流实例
workflow = BasicDatalabWorkflow.create()

@router.post(
    "/analyze",
    response_model=AssistantResponse,
    summary="分析数据处理需求并生成Python命令",
    description="分析用户的数据处理需求，返回相应的Python/Pandas命令或请求更多信息"
)
async def analyze_operation(
        request: AnalysisRequest,
        user_id: str = Depends(get_user_id),
) -> AssistantResponse:
    """分析数据处理需求并生成Python命令"""
    try:
        if not request.table_info:
            raise HTTPException(
                status_code=400,
                detail="必须提供至少一个文件的信息"
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
        logger.error(f"处理数据工坊请求失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理请求时发生错误: {str(e)}"
        )