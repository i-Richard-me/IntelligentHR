from typing import Optional, Any
from fastapi import HTTPException

class TableManagerError(Exception):
    """表格管理基础异常类"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class TableNotFoundError(TableManagerError):
    """表格不存在异常"""
    def __init__(self, database: str, table_name: str):
        self.database = database
        self.table_name = table_name
        message = f"Table '{table_name}' not found in database '{database}'"
        super().__init__(message)

class DatabaseNotFoundError(TableManagerError):
    """数据库不存在异常"""
    def __init__(self, database: str):
        self.database = database
        message = f"Database '{database}' not found"
        super().__init__(message)

class RecordNotFoundError(TableManagerError):
    """记录不存在异常"""
    def __init__(self, table_name: str, record_id: Any):
        self.table_name = table_name
        self.record_id = record_id
        message = f"Record with id '{record_id}' not found in table '{table_name}'"
        super().__init__(message)

class InvalidFilterError(TableManagerError):
    """无效的过滤条件异常"""
    def __init__(self, field: str, operator: str, value: Any):
        self.field = field
        self.operator = operator
        self.value = value
        message = f"Invalid filter condition: field='{field}', operator='{operator}', value='{value}'"
        super().__init__(message)

class InvalidSortError(TableManagerError):
    """无效的排序条件异常"""
    def __init__(self, field: str):
        self.field = field
        message = f"Invalid sort field: '{field}'"
        super().__init__(message)

class ValidationError(TableManagerError):
    """数据验证异常"""
    def __init__(self, message: str):
        super().__init__(message)

class OperationNotAllowedError(TableManagerError):
    """操作不允许异常"""
    def __init__(self, operation: str, reason: str):
        self.operation = operation
        self.reason = reason
        message = f"Operation '{operation}' not allowed: {reason}"
        super().__init__(message)

def handle_table_manager_error(error: TableManagerError) -> HTTPException:
    """转换内部异常为HTTP异常"""
    status_code = 500
    if isinstance(error, TableNotFoundError):
        status_code = 404
    elif isinstance(error, DatabaseNotFoundError):
        status_code = 404
    elif isinstance(error, RecordNotFoundError):
        status_code = 404
    elif isinstance(error, InvalidFilterError):
        status_code = 400
    elif isinstance(error, InvalidSortError):
        status_code = 400
    elif isinstance(error, ValidationError):
        status_code = 400
    elif isinstance(error, OperationNotAllowedError):
        status_code = 403

    return HTTPException(
        status_code=status_code,
        detail=str(error)
    )