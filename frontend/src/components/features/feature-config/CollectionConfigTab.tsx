'use client';

import { useState } from 'react';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { CollectionConfigDialog } from './CollectionConfigDialog';
import { useCollectionConfigs } from '@/hooks/features/feature-config/useCollectionConfigs';
import { CollectionConfig } from '@/types/table-manager';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export function CollectionConfigTab() {
  const { toast } = useToast();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<CollectionConfig | null>(null);

  const {
    configs,
    loading,
    error,
    createConfig,
    updateConfig,
    deleteConfig,
    refresh
  } = useCollectionConfigs();

  // 处理创建配置
  const handleCreate = async (data: Partial<CollectionConfig>) => {
    try {
      await createConfig(data);
      toast({
        title: "创建成功",
        description: "Collection配置已添加",
      });
      setIsCreateDialogOpen(false);
      refresh();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "创建失败",
        description: error instanceof Error ? error.message : "请稍后重试",
      });
    }
  };

  // 处理更新配置
  const handleUpdate = async (data: Partial<CollectionConfig>) => {
    if (!selectedConfig) return;

    try {
      await updateConfig(selectedConfig.name, data);
      toast({
        title: "更新成功",
        description: "Collection配置已更新",
      });
      setIsEditDialogOpen(false);
      setSelectedConfig(null);
      refresh();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "更新失败",
        description: error instanceof Error ? error.message : "请稍后重试",
      });
    }
  };

  // 处理删除配置
  const handleDelete = async () => {
    if (!selectedConfig) return;

    try {
      await deleteConfig(selectedConfig.name);
      toast({
        title: "删除成功",
        description: "Collection配置已删除",
      });
      setIsDeleteDialogOpen(false);
      setSelectedConfig(null);
      refresh();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "删除失败",
        description: error instanceof Error ? error.message : "请稍后重试",
      });
    }
  };

  // 处理编辑按钮点击
  const handleEditClick = (config: CollectionConfig) => {
    setSelectedConfig(config);
    setIsEditDialogOpen(true);
  };

  // 处理删除按钮点击
  const handleDeleteClick = (config: CollectionConfig) => {
    setSelectedConfig(config);
    setIsDeleteDialogOpen(true);
  };

  if (error) {
    return (
      <div className="rounded-md bg-destructive/15 p-4 text-sm text-destructive">
        {error instanceof Error ? error.message : "加载数据失败"}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 操作栏 */}
      <div className="flex justify-between items-center">
        <div className="space-x-2">
          <Button
            onClick={() => setIsCreateDialogOpen(true)}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            添加Collection
          </Button>
        </div>
      </div>

      {/* 数据表格 */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Collection名称</TableHead>
              <TableHead>描述</TableHead>
              <TableHead>字段数</TableHead>
              <TableHead>向量字段</TableHead>
              <TableHead>可用数据库</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              // 加载态
              Array.from({ length: 3 }).map((_, index) => (
                <TableRow key={index}>
                  {Array.from({ length: 6 }).map((_, cellIndex) => (
                    <TableCell key={cellIndex}>
                      <Skeleton className="h-6 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : configs.length === 0 ? (
              // 空状态
              <TableRow>
                <TableCell colSpan={6} className="text-center h-32">
                  暂无Collection配置
                </TableCell>
              </TableRow>
            ) : (
              // 数据展示
              configs.map((config) => (
                <TableRow key={config.name}>
                  <TableCell>
                    <Badge variant="outline">{config.name}</Badge>
                  </TableCell>
                  <TableCell className="max-w-md truncate">
                    {config.description || '-'}
                  </TableCell>
                  <TableCell>{config.fields.length}</TableCell>
                  <TableCell>
                    {config.embedding_fields.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {config.embedding_fields.map(field => (
                          <Badge key={field} variant="secondary">
                            {field}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {config.allowed_databases.map(db => (
                        <Badge key={db} variant="secondary">
                          {db}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEditClick(config)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(config)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 创建Collection对话框 */}
      <CollectionConfigDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        onSubmit={handleCreate}
      />

      {/* 编辑Collection对话框 */}
      {selectedConfig && (
        <CollectionConfigDialog
          open={isEditDialogOpen}
          onOpenChange={setIsEditDialogOpen}
          defaultValues={selectedConfig}
          onSubmit={handleUpdate}
        />
      )}

      {/* 删除确认对话框 */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除Collection &quot;{selectedConfig?.name}&quot; 吗？此操作不可撤销。
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