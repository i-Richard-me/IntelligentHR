'use client';

import { useState, useEffect } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from '@/components/ui/skeleton';
import { Plus } from "lucide-react";
import { CleaningUploadForm } from '@/components/features/data-cleaning/CleaningUploadForm';
import { CleaningTaskList } from '@/components/features/data-cleaning/CleaningTaskList';
import { useCleaningTaskList } from '@/hooks/features/data-cleaning/useCleaningTaskList';
import { useToast } from '@/hooks/use-toast';

export default function DataCleaningPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const {
    tasks,
    entityTypes,
    loading,
    error,
    fetchTasks,
    fetchEntityTypes,
    downloadResult,
    cancelTask
  } = useCleaningTaskList();
  const { toast } = useToast();

  useEffect(() => {
    // 初始化加载实体类型和任务列表
    fetchEntityTypes();
    fetchTasks();
    // 设置定时刷新
    const interval = setInterval(fetchTasks, 60000); // 每分钟刷新一次
    return () => clearInterval(interval);
  }, [fetchTasks, fetchEntityTypes]);

  const handleUploadSuccess = () => {
    fetchTasks();
    setIsDialogOpen(false);
  };

  const handleCancel = async (taskId: string) => {
    try {
      await cancelTask(taskId);
      // fetchTasks() 已经在 cancelTask 中调用了
    } catch (error) {
      // 错误处理已经在 cancelTask 中完成了
    }
  };

  return (
    <div className="flex-1 space-y-8 p-4 md:p-8 pt-6">
      {/* 标题区域 */}
      <div className="border-b pb-6">
        <div className="container px-0">
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            {/* 标题和描述 */}
            <div className="space-y-3">
              <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground/90">
                数据清洗
              </h1>
              <p className="text-sm md:text-base text-muted-foreground max-w-3xl">
                利用 AI 自动识别和标准化实体名称，支持多种实体类型，帮助您快速清理和规范化数据。
              </p>
            </div>

            {/* 操作按钮 */}
            <div className="flex items-center">
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="w-full md:w-auto flex items-center gap-2">
                    <Plus className="h-4 w-4" />
                    创建任务
                  </Button>
                </DialogTrigger>
                <CleaningUploadForm
                  open={isDialogOpen}
                  onOpenChange={setIsDialogOpen}
                  onSuccess={handleUploadSuccess}
                  entityTypes={entityTypes}
                />
              </Dialog>
            </div>
          </div>
        </div>
      </div>

      {/* 任务列表卡片 */}
      <Card>
        <CardHeader>
          <CardTitle>任务列表</CardTitle>
          <CardDescription>
            查看所有数据清洗任务的状态和进度，下载已完成的清洗结果。
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>
                {error instanceof Error ? error.message : '加载任务列表失败'}
              </AlertDescription>
            </Alert>
          )}

          {loading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              暂无清洗任务
            </div>
          ) : (
            <CleaningTaskList
              tasks={tasks}
              entityTypes={entityTypes}
              onDownload={downloadResult}
              onCancel={handleCancel}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}