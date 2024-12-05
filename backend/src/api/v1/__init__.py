from fastapi import APIRouter
from .text_review.routes import router as text_review_router
from .text_classification.routes import router as text_classification_router
from .data_cleaning.routes import router as data_cleaning_router

# 创建v1版本的路由器
v1_router = APIRouter(prefix="/v1")

# 注册文本评估路由
v1_router.include_router(text_review_router)
# 注册文本分类路由
v1_router.include_router(text_classification_router)
# 注册数据清洗路由
v1_router.include_router(data_cleaning_router)