import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import MetaData, Table, select, insert, update, delete, func
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select
from datetime import datetime

from ..models.schemas import (
    TableQueryParams, TableSchema, TableSchemaField,
    TableRecord, QueryResult, BatchOperationResult,
    PaginationParams, SortCondition
)
from ..exceptions.table_exceptions import (
    DatabaseNotFoundError, TableNotFoundError,
    RecordNotFoundError, ValidationError
)
from common.database.connections import db_connections

logger = logging.getLogger(__name__)

class TableService:
    """表格管理服务类"""
    
    def __init__(self, database: str):
        """初始化表格管理服务
        
        Args:
            database: 数据库名称
        
        Raises:
            DatabaseNotFoundError: 如果数据库不存在
        """
        self.database = database
        self.engine = db_connections.get_engine(database)
        if not self.engine:
            raise DatabaseNotFoundError(database)
        
        self.metadata = MetaData()
        logger.info(f"TableService initialized for database: {database}")

    def _get_table(self, table_name: str) -> Table:
        """获取表格对象
        
        Args:
            table_name: 表格名称
            
        Returns:
            Table: SQLAlchemy表格对象
            
        Raises:
            TableNotFoundError: 如果表格不存在
        """
        if table_name not in self.metadata.tables:
            # 反射表结构
            try:
                Table(table_name, self.metadata, autoload_with=self.engine)
            except Exception as e:
                logger.error(f"Failed to load table {table_name}: {str(e)}")
                raise TableNotFoundError(self.database, table_name)
                
        return self.metadata.tables[table_name]

    def get_schema(self, table_name: str) -> TableSchema:
        """获取表格结构
        
        Args:
            table_name: 表格名称
            
        Returns:
            TableSchema: 表格结构信息
        """
        table = self._get_table(table_name)
        
        fields = []
        primary_keys = []
        
        for column in table.columns:
            field = TableSchemaField(
                name=column.name,
                type=str(column.type),
                nullable=column.nullable,
                primary_key=column.primary_key,
                default=column.default.arg if column.default else None,
                description=column.comment
            )
            fields.append(field)
            
            if column.primary_key:
                primary_keys.append(column.name)
        
        return TableSchema(
            table_name=table_name,
            fields=fields,
            primary_keys=primary_keys,
            description=table.comment
        )

    def _build_query(
        self,
        table: Table,
        pagination: Optional[PaginationParams] = None,
        sorts: Optional[List[SortCondition]] = None,
    ) -> Tuple[Select, int]:
        """构建查询对象
        
        Args:
            table: SQLAlchemy表格对象
            pagination: 分页参数
            sorts: 排序条件
            
        Returns:
            Tuple[Select, int]: 查询对象和总记录数
        """
        # 基础查询
        query = select(table)
        
        # 获取总记录数
        count_query = select(func.count()).select_from(table)
        
        # 添加排序
        if sorts:
            for sort in sorts:
                column = table.columns[sort.field]
                query = query.order_by(
                    column.desc() if sort.order == "desc" else column.asc()
                )
        
        # 添加分页
        if pagination:
            offset = (pagination.page - 1) * pagination.page_size
            query = query.offset(offset).limit(pagination.page_size)
        
        return query, count_query

    def list_records(
        self,
        table_name: str,
        pagination: Optional[PaginationParams] = None,
        sorts: Optional[List[SortCondition]] = None,
    ) -> QueryResult:
        """获取记录列表
        
        Args:
            table_name: 表格名称
            pagination: 分页参数
            sorts: 排序条件
            
        Returns:
            QueryResult: 查询结果
        """
        table = self._get_table(table_name)
        query, count_query = self._build_query(table, pagination, sorts)
        
        with Session(self.engine) as session:
            # 执行查询
            total = session.scalar(count_query)
            results = session.execute(query).fetchall()
            
            # 转换结果
            records = []
            for row in results:
                record_dict = row._asdict()
                record = TableRecord(
                    id=record_dict.get(table.primary_key.columns.keys()[0]),
                    data=record_dict,
                    created_at=record_dict.get('created_at'),
                    updated_at=record_dict.get('updated_at')
                )
                records.append(record)
        
        return QueryResult(
            total=total,
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else len(records),
            data=records
        )

    def get_record(self, table_name: str, record_id: Any) -> TableRecord:
        """获取单条记录
        
        Args:
            table_name: 表格名称
            record_id: 记录ID
            
        Returns:
            TableRecord: 记录详情
            
        Raises:
            RecordNotFoundError: 如果记录不存在
        """
        table = self._get_table(table_name)
        primary_key = table.primary_key.columns.keys()[0]
        
        query = select(table).where(table.columns[primary_key] == record_id)
        
        with Session(self.engine) as session:
            result = session.execute(query).first()
            if not result:
                raise RecordNotFoundError(table_name, record_id)
            
            record_dict = result._asdict()
            return TableRecord(
                id=record_dict.get(primary_key),
                data=record_dict,
                created_at=record_dict.get('created_at'),
                updated_at=record_dict.get('updated_at')
            )

    def create_records(
        self,
        table_name: str,
        records: List[Dict[str, Any]]
    ) -> BatchOperationResult:
        """创建记录
        
        Args:
            table_name: 表格名称
            records: 记录列表
            
        Returns:
            BatchOperationResult: 批量操作结果
        """
        table = self._get_table(table_name)
        errors = []
        success_count = 0
        
        with Session(self.engine) as session:
            try:
                for record in records:
                    try:
                        # 添加创建时间
                        if 'created_at' in table.columns:
                            record['created_at'] = datetime.now()
                        if 'updated_at' in table.columns:
                            record['updated_at'] = datetime.now()
                            
                        stmt = insert(table).values(**record)
                        session.execute(stmt)
                        success_count += 1
                    except Exception as e:
                        errors.append({
                            "data": record,
                            "error": str(e)
                        })
                        
                session.commit()
            except Exception as e:
                session.rollback()
                raise ValidationError(f"Batch insert failed: {str(e)}")
        
        return BatchOperationResult(
            success_count=success_count,
            error_count=len(errors),
            errors=errors if errors else None
        )

    def update_record(
        self,
        table_name: str,
        record_id: Any,
        data: Dict[str, Any]
    ) -> TableRecord:
        """更新记录
        
        Args:
            table_name: 表格名称
            record_id: 记录ID
            data: 更新数据
            
        Returns:
            TableRecord: 更新后的记录
            
        Raises:
            RecordNotFoundError: 如果记录不存在
            ValidationError: 如果更新数据无效
        """
        table = self._get_table(table_name)
        primary_key = table.primary_key.columns.keys()[0]
        
        # 添加更新时间
        if 'updated_at' in table.columns:
            data['updated_at'] = datetime.now()
            
        with Session(self.engine) as session:
            try:
                # 检查记录是否存在
                record = self.get_record(table_name, record_id)
                
                # 执行更新
                stmt = update(table).where(
                    table.columns[primary_key] == record_id
                ).values(**data)
                session.execute(stmt)
                session.commit()
                
                # 获取更新后的记录
                return self.get_record(table_name, record_id)
            except RecordNotFoundError:
                raise
            except Exception as e:
                session.rollback()
                raise ValidationError(f"Update failed: {str(e)}")

    def delete_record(self, table_name: str, record_id: Any) -> bool:
        """删除记录
        
        Args:
            table_name: 表格名称
            record_id: 记录ID
            
        Returns:
            bool: 是否删除成功
            
        Raises:
            RecordNotFoundError: 如果记录不存在
        """
        table = self._get_table(table_name)
        primary_key = table.primary_key.columns.keys()[0]
        
        with Session(self.engine) as session:
            try:
                # 检查记录是否存在
                self.get_record(table_name, record_id)
                
                # 执行删除
                stmt = delete(table).where(table.columns[primary_key] == record_id)
                session.execute(stmt)
                session.commit()
                return True
            except RecordNotFoundError:
                raise
            except Exception as e:
                session.rollback()
                raise ValidationError(f"Delete failed: {str(e)}")