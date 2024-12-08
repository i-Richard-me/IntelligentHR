'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getPaginationRowModel,
} from "@tanstack/react-table";
import { useCollectionData } from '@/hooks/features/feature-config/useCollectionData';
import { useCollectionConfigs } from '@/hooks/features/feature-config/useCollectionConfigs';
import { CollectionConfig } from '@/types/table-manager';
import { Search, Upload, Trash2, Pencil } from 'lucide-react';
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
import { DataTablePagination } from '@/components/shared/tables/DataTablePagination';
import { Skeleton } from '@/components/ui/skeleton';
import { DataUploadDialog } from './DataUploadDialog';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { Checkbox } from "@/components/ui/checkbox";

// 支持的数据库列表
const SUPPORTED_DATABASES = [
  { id: 'data_cleaning', name: '数据清洗库' },
  { id: 'production', name: '生产库' },
  { id: 'examples', name: '示例库' },
];

interface DataTableProps {
  columns: ColumnDef<any>[];
  data: any[];
  pageCount: number;
  onPaginationChange: (pagination: { pageIndex: number; pageSize: number }) => void;
}

export function CollectionDataTab() {
  const { toast } = useToast();
  const [selectedDatabase, setSelectedDatabase] = useState<string | undefined>();
  const [selectedCollection, setSelectedCollection] = useState<CollectionConfig | null>(null);
  const [searchField, setSearchField] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [{ pageIndex, pageSize }, setPagination] = useState({
    pageIndex: 0,
    pageSize: 10,
  });
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [recordToDelete, setRecordToDelete] = useState<string | null>(null);
  const [recordToEdit, setRecordToEdit] = useState<Record<string, any> | null>(null);

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
    formatTableData,
    batchDelete
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
    setPagination(prev => ({ ...prev, pageIndex: 0 }));
  }, []);

  // 处理 Collection 选择
  const handleCollectionChange = useCallback((collectionName: string) => {
    const collection = availableCollections.find(c => c.name === collectionName);
    setSelectedCollection(collection || null);
    setSearchField(null);
    setSearchText('');
    setPagination(prev => ({ ...prev, pageIndex: 0 }));
  }, [availableCollections]);

  // 处理搜索
  const handleSearch = useCallback(() => {
    if (!selectedDatabase || !selectedCollection) return;

    queryData({
      page: pageIndex + 1,
      page_size: pageSize,
      search_field: searchField || undefined,
      search_text: searchText,
      top_k: searchField ? pageSize : undefined
    });
  }, [queryData, pageIndex, pageSize, searchField, searchText, selectedDatabase, selectedCollection]);

  // 获取可搜索字段（向量字段）
  const getSearchableFields = useCallback(() => {
    if (!selectedCollection) return [];
    return selectedCollection.fields.filter(field => field.is_vector);
  }, [selectedCollection]);

  // 处理删除确认
  const handleDelete = async () => {
    if (!recordToDelete) return;

    try {
      await batchDelete({ ids: [recordToDelete] });
      toast({
        title: "删除成功",
        description: "数据已删除",
      });
      // 刷新数据
      queryData({
        page: pageIndex + 1,
        page_size: pageSize,
        search_field: searchField || undefined,
        search_text: searchText,
        top_k: searchField ? pageSize : undefined
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "删除失败",
        description: error instanceof Error ? error.message : "请稍后重试",
      });
    } finally {
      setIsDeleteDialogOpen(false);
      setRecordToDelete(null);
    }
  };

  // 处理批量删除
  const handleBatchDelete = async () => {
    if (selectedRows.length === 0) return;

    try {
      await batchDelete({ ids: selectedRows });
      toast({
        title: "批量删除成功",
        description: `已删除 ${selectedRows.length} 条数据`,
      });
      // 刷新数据
      queryData({
        page: pageIndex + 1,
        page_size: pageSize,
        search_field: searchField || undefined,
        search_text: searchText,
        top_k: searchField ? pageSize : undefined
      });
      setSelectedRows([]);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "批量删除失败",
        description: error instanceof Error ? error.message : "请稍后重试",
      });
    }
  };

  // 构建表格列配置
  const columns = useMemo<ColumnDef<any>[]>(() => {
    if (!selectedCollection) return [];
    
    const baseColumns = getTableColumns().map(col => ({
      accessorKey: col.field,
      header: col.title,
    }));

    return [
      {
        id: 'select',
        header: ({ table }) => (
          <Checkbox
            checked={table.getIsAllPageRowsSelected()}
            onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
            aria-label="Select all"
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
          />
        ),
        enableSorting: false,
        enableHiding: false,
      },
      ...baseColumns,
      {
        accessorKey: 'distance',
        header: '相似度',
        cell: ({ row }) => {
          const distance = row.original.distance;
          return distance ? `${(distance * 100).toFixed(2)}%` : '-';
        },
      },
      {
        id: 'actions',
        header: ({ column }) => (
          <div className="text-right">操作</div>
        ),
        cell: ({ row }) => {
          const record = row.original;
          return (
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  // 准备编辑数据
                  const editData = { ...record };
                  delete editData.id;  // 移除 id 字段
                  delete editData.distance;  // 移除 distance 字段
                  setRecordToEdit(editData);
                  setIsUploadDialogOpen(true);
                }}
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setRecordToDelete(record.id);
                  setIsDeleteDialogOpen(true);
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          );
        },
      },
    ];
  }, [selectedCollection, getTableColumns]);

  // 处理分页变化
  const handlePaginationChange = useCallback(
    ({ pageIndex, pageSize }: { pageIndex: number; pageSize: number }) => {
      setPagination({ pageIndex, pageSize });
      queryData({
        page: pageIndex + 1,
        page_size: pageSize,
        search_field: searchField || undefined,
        search_text: searchText,
        top_k: searchField ? pageSize : undefined
      });
    },
    [queryData, searchField, searchText]
  );

  // 初始化表格
  const table = useReactTable({
    data: formatTableData(data) || [],
    columns,
    pageCount: data ? Math.ceil(data.total / pageSize) : -1,
    state: {
      pagination: {
        pageIndex,
        pageSize,
      },
    },
    onPaginationChange: (updater) => {
      const newPagination = 
        typeof updater === 'function' 
          ? updater({ pageIndex, pageSize })
          : updater;
      setPagination(newPagination);
      queryData({
        page: newPagination.pageIndex + 1,
        page_size: newPagination.pageSize,
        search_field: searchField || undefined,
        search_text: searchText,
        top_k: searchField ? newPagination.pageSize : undefined
      });
    },
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
  });

  // 初始化加载数据
  useEffect(() => {
    if (selectedDatabase && selectedCollection) {
      queryData({
        page: pageIndex + 1,
        page_size: pageSize,
        search_field: searchField || undefined,
        search_text: searchText,
        top_k: searchField ? pageSize : undefined
      });
    }
  }, [selectedDatabase, selectedCollection]);

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

      {/* 操作栏 */}
      <div className="flex justify-between items-center">
        <div className="space-x-2">
          <Button
            onClick={() => {
              setRecordToEdit(null);  // 清空编辑数据，表示新建
              setIsUploadDialogOpen(true);
            }}
            className="flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            导入数据
          </Button>
          {selectedRows.length > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleBatchDelete}
              className="flex items-center gap-2"
            >
              <Trash2 className="h-4 w-4" />
              删除选中 ({selectedRows.length})
            </Button>
          )}
        </div>
        <div className="flex items-center gap-4">
          {/* ... existing search components ... */}
        </div>
      </div>

      {/* 数据表格区域 */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
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
                  colSpan={columns.length}
                  className="text-center text-destructive h-32"
                >
                  {error.message}
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows?.length ? (
              // 数据展示
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              // 空状态
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-center h-32"
                >
                  暂无数据
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页区域 */}
      {data && <DataTablePagination table={table} />}

      {/* 数据上传/编辑对话框 */}
      {selectedCollection && (
        <DataUploadDialog
          open={isUploadDialogOpen}
          onOpenChange={(open) => {
            setIsUploadDialogOpen(open);
            if (!open) {
              setRecordToEdit(null);  // 关闭对话框时清空编辑数据
            }
          }}
          collection={selectedCollection}
          database={selectedDatabase || ''}
          editData={recordToEdit}  // 传递编辑数据
          onSuccess={() => {
            // 刷新数据
            queryData({
              page: pageIndex + 1,
              page_size: pageSize,
              search_field: searchField || undefined,
              search_text: searchText,
              top_k: searchField ? pageSize : undefined
            });
          }}
        />
      )}

      {/* 删除确认对话框 */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除这条数据吗？此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}