'use client';

import { useState, useCallback, useMemo } from 'react';
import { useCollectionData } from '@/hooks/features/feature-config/useCollectionData';
import { useCollectionConfigs } from '@/hooks/features/feature-config/useCollectionConfigs';
import { CollectionConfig } from '@/types/table-manager';
import { Search } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from '@/components/ui/button';
import { SimplePagination } from '@/components/shared/tables/SimplePagination';
import { Skeleton } from '@/components/ui/skeleton';
import { DataUploadDialog } from './DataUploadDialog';

// 支持的数据库列表
const SUPPORTED_DATABASES = [
  { id: 'data_cleaning', name: '数据清洗库' },
  { id: 'production', name: '生产库' },
  { id: 'examples', name: '示例库' },
];

export function CollectionDataTab() {
  const { toast } = useToast();
  const [selectedDatabase, setSelectedDatabase] = useState<string | undefined>();
  const [selectedCollection, setSelectedCollection] = useState<CollectionConfig | null>(null);
  const [searchField, setSearchField] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);

  // 获取 Collection 配置列表
  const {
    configs: allCollections,
    loading: loadingCollections,
  } = useCollectionConfigs();

  // 根据选择的数据库筛选可用的 collections
  const availableCollections = useMemo(() => {
    if (!selectedDatabase) return [];
    return allCollections.filter(collection =>
      collection.collection_databases.includes(selectedDatabase)
    );
  }, [selectedDatabase, allCollections]);

  // 使用 Collection 数据管理 Hook
  const {
    data,
    loading: loadingData,
    error,
    queryData,
    getTableColumns,
    formatTableData
  } = useCollectionData({
    database: selectedDatabase,
    collection: selectedCollection
  });

  // 处理数据库选择
  const handleDatabaseChange = useCallback((databaseId: string) => {
    setSelectedDatabase(databaseId);
    setSelectedCollection(null);
    setSearchField(null);
    setSearchText('');
    setPage(1);
  }, []);

  // 处理 Collection 选择
  const handleCollectionChange = useCallback((collectionName: string) => {
    const collection = availableCollections.find(c => c.name === collectionName);
    setSelectedCollection(collection || null);
    setSearchField(null);
    setSearchText('');
    setPage(1);
  }, [availableCollections]);

  // 处理搜索
  const handleSearch = useCallback(() => {
    if (!selectedDatabase || !selectedCollection) return;

    queryData({
      page,
      page_size: pageSize,
      search_field: searchField || undefined,
      search_text: searchText,
      top_k: searchField ? pageSize : undefined
    });
  }, [queryData, page, pageSize, searchField, searchText, selectedDatabase, selectedCollection]);

  // 获取可搜索字段（向量字段）
  const getSearchableFields = useCallback(() => {
    if (!selectedCollection) return [];
    return selectedCollection.fields.filter(field => field.is_vector);
  }, [selectedCollection]);

  // 表格列配置
  const columns = selectedCollection ? getTableColumns() : [];

  // 格式化表格数据
  const tableData = formatTableData(data);

  return (
    <div className="space-y-6">
      {/* 数据库和Collection选择区域 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        {/* 数据库选择 */}
        <div className="flex-1 space-y-2">
          <Label>选择数据库</Label>
          <Select
            value={selectedDatabase}
            onValueChange={handleDatabaseChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="请选择数据库" />
            </SelectTrigger>
            <SelectContent>
              {SUPPORTED_DATABASES.map(db => (
                <SelectItem key={db.id} value={db.id}>
                  {db.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Collection选择 */}
        {selectedDatabase && (
          <div className="flex-1 space-y-2">
            <Label>选择Collection</Label>
            <Select
              value={selectedCollection?.name}
              onValueChange={handleCollectionChange}
              disabled={loadingCollections}
            >
              <SelectTrigger>
                <SelectValue placeholder="请选择要管理的Collection" />
              </SelectTrigger>
              <SelectContent>
                {availableCollections.map(collection => (
                  <SelectItem key={collection.name} value={collection.name}>
                    {collection.display_name || collection.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* 搜索区域 */}
        {selectedCollection && (
          <>
            <div className="flex-1 space-y-2">
              <Label>搜索字段</Label>
              <Select
                value={searchField || undefined}
                onValueChange={setSearchField}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择搜索字段" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">无</SelectItem>
                  {getSearchableFields().map(field => (
                    <SelectItem key={field.name} value={field.name}>
                      {field.description || field.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 space-y-2">
              <Label>搜索内容</Label>
              <div className="flex gap-2">
                <Input
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  placeholder="输入搜索内容"
                />
                <Button
                  onClick={handleSearch}
                  disabled={loadingData}
                >
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* 数据操作按钮区域 */}
      {selectedCollection && (
        <div className="flex justify-between items-center">
          <div>
            <Button
              onClick={() => setIsUploadDialogOpen(true)}
              disabled={loadingData}
            >
              导入数据
            </Button>
          </div>
          <div className="text-sm text-muted-foreground">
            {data?.total ? `共 ${data.total} 条数据` : null}
          </div>
        </div>
      )}

      {/* 数据表格区域 */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column, index) => (
                <TableHead key={index}>
                  {column.title}
                </TableHead>
              ))}
              {columns.length > 0 && <TableHead>相似度</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loadingData ? (
              // 加载状态
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index}>
                  {columns.map((_, cellIndex) => (
                    <TableCell key={cellIndex}>
                      <Skeleton className="h-6" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : error ? (
              // 错误状态
              <TableRow>
                <TableCell
                  colSpan={columns.length + 1}
                  className="text-center text-destructive h-32"
                >
                  {error.message}
                </TableCell>
              </TableRow>
            ) : !tableData.length ? (
              // 空状态
              <TableRow>
                <TableCell
                  colSpan={columns.length + 1}
                  className="text-center h-32"
                >
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              // 数据展示
              tableData.map((row, index) => (
                <TableRow key={index}>
                  {columns.map((column) => (
                    <TableCell key={column.field}>
                      {row[column.field]}
                    </TableCell>
                  ))}
                  <TableCell>
                    {row.distance ? (
                      `${(row.distance * 100).toFixed(2)}%`
                    ) : '-'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页区域 */}
      {data && (
        <SimplePagination
          pageSize={pageSize}
          setPageSize={setPageSize}
          page={page}
          setPage={setPage}
          total={data.total}
        />
      )}

      {/* 数据上传对话框 */}
      {selectedCollection && selectedDatabase && (
        <DataUploadDialog
          open={isUploadDialogOpen}
          onOpenChange={setIsUploadDialogOpen}
          collection={selectedCollection}
          database={selectedDatabase}
          onSuccess={() => {
            handleSearch();
            toast({
              title: "上传成功",
              description: "数据已成功导入",
            });
          }}
        />
      )}
    </div>
  );
}