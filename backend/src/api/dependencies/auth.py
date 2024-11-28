from fastapi import Header, HTTPException
from typing import Optional

async def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """用户认证依赖
    
    验证请求头中是否包含用户ID
    
    Args:
        x_user_id: 请求头中的用户ID

    Returns:
        str: 用户ID

    Raises:
        HTTPException: 当请求头中缺少用户ID时抛出401错误
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id