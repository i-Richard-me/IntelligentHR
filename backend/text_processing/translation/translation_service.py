from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from backend.text_processing.translation.translator import Translator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translation")


class TranslationRequest(BaseModel):
    text: str
    text_topic: str


class TranslationResponse(BaseModel):
    translated_text: str


translation_service: Optional[Translator] = None


def initialize_translation_service():
    global translation_service
    if translation_service is None:
        translation_service = Translator()
        logger.info("翻译服务初始化完成。")


@router.post("", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    if translation_service is None:
        raise HTTPException(status_code=503, detail="翻译服务未启动")

    try:
        translated_text = await translation_service.translate(
            request.text, request.text_topic
        )
        return TranslationResponse(translated_text=translated_text)
    except ValueError as ve:
        logger.error(f"翻译结果格式错误: {ve}")
        raise HTTPException(status_code=500, detail=f"翻译结果格式错误: {ve}")
    except Exception as e:
        logger.error(f"翻译过程中发生错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"翻译过程中发生错误: {e}")


def get_translation_service_status():
    return "running" if translation_service else "not running"
