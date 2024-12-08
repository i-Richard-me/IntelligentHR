'use client';

import { useState, useEffect } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from '@/components/ui/skeleton';
import { Plus } from "lucide-react";
import ClassificationUploadForm from '@/components/features/text-classification/ClassificationUploadForm';
import { ClassificationTaskList } from '@/components/features/text-classification/ClassificationTaskList';
import { useClassificationTaskList } from '@/hooks/features/text-classification/useClassificationTaskList';

export default function TextClassificationPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const {
    tasks,
    loading,
    error,
    fetchTasks,
    downloadResult,
    cancelTask
  } = useClassificationTaskList();

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 60000); // 每分钟刷新一次
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const handleUploadSuccess = () => {
    fetchTasks();
    setIsDialogOpen(false);
  };

  const handleCancel = async (taskId: string) => {
    try {
      await cancelTask(taskId);
    } catch (error) {
      console.error('Cancel task failed:', error);
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
                文本分类
              </h1>
              <p className="text-sm md:text-base text-muted-foreground max-w-3xl">
                通过 AI 对文本进行智能分类，支持自定义分类规则，可选择单标签或多标签分类模式。
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
                <ClassificationUploadForm
                  open={isDialogOpen}
                  onOpenChange={setIsDialogOpen}
                  onSuccess={handleUploadSuccess}
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
            查看和管理分类任务，支持实时进度跟踪和结果下载。
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
              暂无分类任务
            </div>
          ) : (
            <ClassificationTaskList
              tasks={tasks}
              onDownload={downloadResult}
              onCancel={handleCancel}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}