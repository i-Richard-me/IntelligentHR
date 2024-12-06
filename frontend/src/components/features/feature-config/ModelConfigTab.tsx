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
import { ModelConfigDialog } from './ModelConfigDialog';
import { useModelConfigs } from '@/hooks/features/feature-config/useModelConfigs';
import { AnalysisModelConfig } from '@/types/table-manager';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export function ModelConfigTab() {
  const { toast } = useToast();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<AnalysisModelConfig | null>(null);

  const {
    configs,
    loading,
    error,
    createConfig,
    updateConfig,
    deleteConfig,
    refresh
  } = useModelConfigs();

  // 处理创建配置
  const handleCreate = async (data: Partial<AnalysisModelConfig>) => {
    try {
      await createConfig(data);
      toast({
        title: "创建成功",
        description: "新的业务分析模型已添加",
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
  const handleUpdate = async (data: Partial<AnalysisModelConfig>) => {
    if (!selectedConfig) return;

    try {
      await updateConfig(selectedConfig.entity_type, data);
      toast({
        title: "更新成功",
        description: "业务分析模型已更新",
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
      await deleteConfig(selectedConfig.entity_type);
      toast({
        title: "删除成功",
        description: "业务分析模型已删除",
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
  const handleEditClick = (config: AnalysisModelConfig) => {
    setSelectedConfig(config);
    setIsEditDialogOpen(true);
  };

  // 处理删除按钮点击
  const handleDeleteClick = (config: AnalysisModelConfig) => {
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
            添加模型
          </Button>
        </div>
      </div>

      {/* 数据表格 */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>模型标识</TableHead>
              <TableHead>显示名称</TableHead>
              <TableHead>描述</TableHead>
              <TableHead>集合名称</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              // 加载态
              Array.from({ length: 3 }).map((_, index) => (
                <TableRow key={index}>
                  {Array.from({ length: 5 }).map((_, cellIndex) => (
                    <TableCell key={cellIndex}>
                      <Skeleton className="h-6 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : configs.length === 0 ? (
              // 空状态
              <TableRow>
                <TableCell colSpan={5} className="text-center h-32">
                  暂无模型配置
                </TableCell>
              </TableRow>
            ) : (
              // 数据展示
              configs.map((config) => (
                <TableRow key={config.entity_type}>
                  <TableCell>
                    <Badge variant="outline">{config.entity_type}</Badge>
                  </TableCell>
                  <TableCell>{config.display_name}</TableCell>
                  <TableCell className="max-w-md truncate">
                    {config.description || '-'}
                  </TableCell>
                  <TableCell>{config.collection_name}</TableCell>
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

      {/* 创建模型对话框 */}
      <ModelConfigDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        onSubmit={handleCreate}
      />

      {/* 编辑模型对话框 */}
      {selectedConfig && (
        <ModelConfigDialog
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
              确定要删除业务分析模型 &quot;{selectedConfig?.display_name}&quot; 吗？此操作不可撤销。
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