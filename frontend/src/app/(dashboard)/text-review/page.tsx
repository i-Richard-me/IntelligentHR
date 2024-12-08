'use client';

import { useState, useEffect } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from '@/components/ui/skeleton';
import { Plus } from "lucide-react";
import UploadForm from '@/components/features/text-review/UploadForm';
import { TaskList } from '@/components/features/text-review/TaskList';
import { useTaskList } from '@/hooks/features/text-review/useTaskList';
import { textReviewApi } from '@/services';
import { useToast } from '@/hooks/use-toast';

export default function TextReviewPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const { tasks, loading, error, fetchTasks } = useTaskList();
  const { toast } = useToast();

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 60000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const handleDownload = async (taskId: string, fileName: string) => {
    try {
      await textReviewApi.downloadResult(taskId, fileName);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const handleUploadSuccess = () => {
    fetchTasks();
    setIsDialogOpen(false);
  };

  const handleCancel = async (taskId: string) => {
    try {
      await textReviewApi.cancelTask(taskId);
      toast({
        title: '已发送取消请求',
        description: '任务将在当前处理完成后停止',
      });
      // 刷新任务列表
      fetchTasks();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: '取消失败',
        description: error instanceof Error ? error.message : '请稍后重试',
      });
    }
  };

  return (
    <div className="flex-1 space-y-8 p-4 md:p-8 pt-6">
      {/* 标题区域 - 使用响应式布局 */}
      <div className="border-b pb-6">
        <div className="container px-0">
          {/* 在移动端时改为垂直布局 */}
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            {/* 标题和描述 */}
            <div className="space-y-3">
              <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground/90">文本评估</h1>
              <p className="text-sm md:text-base text-muted-foreground max-w-3xl">
                通过 AI 批量分析文本的有效性、情感倾向和敏感信息，支持自定义评估场景，快速完成文本审查。
              </p>
            </div>
            
            {/* 操作按钮 */}
            <div className="flex items-center">
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                {/* 移动端显示完整按钮 */}
                <DialogTrigger asChild>
                  <Button className="w-full md:w-auto flex items-center gap-2">
                    <Plus className="h-4 w-4" />
                    创建任务
                  </Button>
                </DialogTrigger>
                <UploadForm 
                  open={isDialogOpen}
                  onOpenChange={setIsDialogOpen}
                  onSuccess={handleUploadSuccess}
                />
              </Dialog>
            </div>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>任务列表</CardTitle>
          <CardDescription>
            查看和管理评估任务，支持实时进度跟踪和结果下载。已完成的任务可下载评估结果。
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
              暂无评估任务
            </div>
          ) : (
            <TaskList 
              tasks={tasks}
              onDownload={handleDownload}
              onCancel={handleCancel}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}