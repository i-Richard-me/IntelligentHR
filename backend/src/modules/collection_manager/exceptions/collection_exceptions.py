from typing import Optional, Any
from fastapi import HTTPException


class CollectionManagerError(Exception):
    """Collection管理基础异常类"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class CollectionNotFoundError(CollectionManagerError):
    """Collection不存在异常"""
    def __init__(self, collection_name: str, database: str):
        self.collection_name = collection_name
        self.database = database
        message = f"Collection '{collection_name}' not found in database '{database}'"
        super().__init__(message)


class DatabaseCollectionNotFoundError(CollectionManagerError):
    """数据库中不存在指定Collection异常"""
    def __init__(self, database: str, collection_name: str):
        self.database = database
        self.collection_name = collection_name
        message = f"Collection '{collection_name}' does not exist in database '{database}'"
        super().__init__(message)


class InvalidDataError(CollectionManagerError):
    """数据无效异常"""
    def __init__(self, detail: str):
        self.detail = detail
        message = f"Invalid data: {detail}"
        super().__init__(message)


class VectorizeError(CollectionManagerError):
    """向量化处理异常"""
    def __init__(self, field: str, detail: str):
        self.field = field
        self.detail = detail
        message = f"Failed to vectorize field '{field}': {detail}"
        super().__init__(message)


class BatchOperationError(CollectionManagerError):
    """批量操作异常"""
    def __init__(self, operation: str, detail: str):
        self.operation = operation
        self.detail = detail
        message = f"Batch {operation} operation failed: {detail}"
        super().__init__(message)


class ConfigurationError(CollectionManagerError):
    """配置错误异常"""
    def __init__(self, detail: str):
        self.detail = detail
        message = f"Configuration error: {detail}"
        super().__init__(message)


def handle_collection_manager_error(error: CollectionManagerError) -> HTTPException:
    """转换内部异常为HTTP异常
    
    Args:
        error: 内部异常实例
        
    Returns:
        HTTPException: 对应的HTTP异常
    """
    status_code = 500
    if isinstance(error, CollectionNotFoundError):
        status_code = 404
    elif isinstance(error, DatabaseCollectionNotFoundError):
        status_code = 403
    elif isinstance(error, InvalidDataError):
        status_code = 400
    elif isinstance(error, VectorizeError):
        status_code = 400
    elif isinstance(error, BatchOperationError):
        status_code = 400
    elif isinstance(error, ConfigurationError):
        status_code = 400

    return HTTPException(
        status_code=status_code,
        detail=str(error)
    )