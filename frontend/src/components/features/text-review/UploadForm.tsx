import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import { useToast } from '@/hooks/use-toast';
import { textReviewApi } from '@/services';

const uploadFormSchema = z.object({
  file: z.custom<File>((v) => v instanceof File, {
    message: '请选择文件',
  }),
  context: z.string().min(1, '请输入评估要求'),
});

type UploadFormValues = z.infer<typeof uploadFormSchema>;

interface UploadFormProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSuccess?: () => void;
}

export default function UploadForm({ open, onOpenChange, onSuccess }: UploadFormProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const { toast } = useToast();

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadFormSchema),
  });

  const onSubmit = async (data: UploadFormValues) => {
    try {
      setUploading(true);
      setProgress(0);
      
      const response = await textReviewApi.createTask({
        file: data.file,
        context: data.context,
      });

      if (response.error) {
        throw new Error(response.error.detail);
      }

      toast({
        title: '创建成功',
        description: '评估任务已开始处理',
      });
      
      form.reset();
      onSuccess?.();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: '创建失败',
        description: error instanceof Error ? error.message : '请稍后重试',
      });
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden p-0 md:max-w-[700px] lg:max-w-[800px]">
        <div className="p-6 pb-0">
          <DialogHeader>
            <DialogTitle>创建评估任务</DialogTitle>
            <DialogDescription>
              上传待评估的CSV文件（需包含text列），并简要说明评估场景。系统将分析文本的有效性、情感倾向和敏感信息。
            </DialogDescription>
          </DialogHeader>
        </div>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-6 p-6">
            <FormField
              control={form.control}
              name="file"
              render={({ field: { onChange, value, ...field } }) => (
                <FormItem>
                  <FormLabel>上传文件</FormLabel>
                  <FormControl>
                    <div className="flex items-center gap-2">
                      <Input
                        type="file"
                        accept=".csv,.xlsx,.xls"
                        disabled={uploading}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            onChange(file);
                          }
                        }}
                        {...field}
                        className="flex-1"
                      />
                      {value && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => onChange(undefined)}
                          className="shrink-0"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </FormControl>
                  <FormDescription>
                    请上传CSV格式文件，文件中需包含text列作为待评估文本
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="context"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>评估场景</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="简要描述评估场景，如：员工调研反馈"
                      disabled={uploading}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    简单描述文本的使用场景，帮助系统更准确地进行评估
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {uploading && progress > 0 && (
              <div className="space-y-2">
                <Progress value={progress} />
                <p className="text-sm text-muted-foreground text-center">
                  {progress}%
                </p>
              </div>
            )}

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange?.(false)}
                disabled={uploading}
              >
                取消
              </Button>
              <Button type="submit" disabled={uploading}>
                {uploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    处理中
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    开始评估
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}