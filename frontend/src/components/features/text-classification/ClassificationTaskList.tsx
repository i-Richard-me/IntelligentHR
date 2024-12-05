import { useMemo } from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { Download, FileText, Tag, Tags, Ban } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { formatDate } from '@/lib/utils';
import { ClassificationTaskResponse, TaskStatus } from '@/types/api';
import { DataTableColumnHeader } from '@/components/shared/tables/DataTableColumnHeader';
import { DataTablePagination } from '@/components/shared/tables/DataTablePagination';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const statusMap = {
  [TaskStatus.WAITING]: { label: '等待中', variant: 'secondary' as const },
  [TaskStatus.PROCESSING]: { label: '处理中', variant: 'default' as const },
  [TaskStatus.COMPLETED]: { label: '已完成', variant: 'secondary' as const },
  [TaskStatus.FAILED]: { label: '失败', variant: 'destructive' as const },
  [TaskStatus.CANCELLED]: { label: '已取消', variant: 'secondary' as const },
};

interface ClassificationTaskListProps {
  tasks: ClassificationTaskResponse[];
  onDownload: (taskId: string, fileName: string) => void;
  onCancel?: (taskId: string) => void;
}

export function ClassificationTaskList({ tasks, onDownload, onCancel }: ClassificationTaskListProps) {
  const columns = useMemo<ColumnDef<ClassificationTaskResponse>[]>(() => [
    {
      accessorKey: 'created_at',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="创建时间" />
      ),
      cell: ({ row }) => (
        <div>{formatDate(row.original.created_at)}</div>
      ),
    },
    {
      accessorKey: 'context',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="分类上下文" />
      ),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="truncate font-medium">
            {row.original.context}
          </span>
        </div>
      ),
    },
    {
      id: 'categories',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="分类规则" />
      ),
      cell: ({ row }) => {
        const task = row.original;
        const categoriesCount = Object.keys(task.categories).length;

        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-2">
                  {task.is_multi_label ? (
                    <Tags className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Tag className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className="font-medium">{categoriesCount} 个类别</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-2">
                  <p className="font-semibold">{task.is_multi_label ? '多标签分类' : '单标签分类'}</p>
                  <ul className="text-sm">
                    {Object.entries(task.categories).map(([name, desc]) => (
                      <li key={name} className="flex items-center gap-2">
                        <Badge variant="outline" className="shrink-0">{name}</Badge>
                        <span className="text-muted-foreground truncate">{desc}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      },
    },
    {
      accessorKey: 'status',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="状态" />
      ),
      cell: ({ row }) => {
        const status = statusMap[row.original.status];
        return (
          <div className="flex items-center gap-2">
            <Badge variant={status.variant}>{status.label}</Badge>
            {row.original.error_message && (
              <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                {row.original.error_message}
              </span>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'total_records',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="总行数" />
      ),
      cell: ({ row }) => {
        const task = row.original;
        return (
          <div className="w-[80px] text-right">
            {task.total_records?.toLocaleString() || '-'}
          </div>
        );
      },
    },
    {
      accessorKey: 'progress',
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="进度" />
      ),
      cell: ({ row }) => {
        const task = row.original;
        const processed = task.processed_records || 0;
        const total = task.total_records || 0;
        const percentage = total > 0 ? Math.round((processed / total) * 100) : 0;

        return (
          <div className="w-[120px]">
            <Progress value={percentage} />
          </div>
        );
      },
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const task = row.original;
        const canDownload = task.status === TaskStatus.COMPLETED;
        const canCancel =
          onCancel &&
          (task.status === TaskStatus.WAITING || task.status === TaskStatus.PROCESSING) &&
          !task.cancellation_requested;

        return (
          <div className="flex items-center gap-2">
            {canDownload && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDownload(
                  task.task_id,
                  `分类结果_${formatDate(task.created_at)}`
                )}
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                <span>下载</span>
              </Button>
            )}
            {canCancel && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onCancel(task.task_id)}
                className="flex items-center gap-2 text-destructive hover:text-destructive"
              >
                <Ban className="h-4 w-4" />
                <span>取消</span>
              </Button>
            )}
          </div>
        );
      },
    },
  ], [onDownload, onCancel]);

  const table = useReactTable({
    data: tasks,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="space-y-4">
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
            {table.getRowModel().rows?.length ? (
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
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  暂无任务数据
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <DataTablePagination table={table} />
    </div>
  );
}