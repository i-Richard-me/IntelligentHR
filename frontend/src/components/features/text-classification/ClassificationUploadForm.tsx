import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Upload, X, Plus, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
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
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';

const uploadFormSchema = z.object({
  file: z.custom<File>((v) => v instanceof File, {
    message: '请选择文件',
  }),
  context: z.string().min(1, '请输入分类要求'),
  categories: z.array(z.object({
    name: z.string().min(1, '请输入类别名称'),
    description: z.string().min(1, '请输入类别描述'),
  })).min(2, '至少需要定义两个分类'),
  is_multi_label: z.boolean().default(false),
});

type UploadFormValues = z.infer<typeof uploadFormSchema>;

interface ClassificationUploadFormProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSuccess?: () => void;
}

export default function ClassificationUploadForm({
  open,
  onOpenChange,
  onSuccess
}: ClassificationUploadFormProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const { toast } = useToast();

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadFormSchema),
    defaultValues: {
      categories: [
        { name: '', description: '' },
        { name: '', description: '' }
      ],
      is_multi_label: false,
    },
  });

  const onSubmit = async (data: UploadFormValues) => {
    try {
      setUploading(true);
      setProgress(0);

      // 将categories数组转换为对象
      const categoriesObject = data.categories.reduce((acc, curr) => {
        acc[curr.name] = curr.description;
        return acc;
      }, {} as Record<string, string>);

      // TODO: 调用创建任务的方法
      // const response = await createTask(data.file, data.context, categoriesObject, data.is_multi_label);

      toast({
        title: '创建成功',
        description: '分类任务已开始处理',
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

  const addCategory = () => {
    const currentCategories = form.getValues('categories');
    form.setValue('categories', [
      ...currentCategories,
      { name: '', description: '' }
    ]);
  };

  const removeCategory = (index: number) => {
    const currentCategories = form.getValues('categories');
    if (currentCategories.length > 2) {
      form.setValue('categories', currentCategories.filter((_, i) => i !== index));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-y-auto max-h-[90vh] p-0 md:max-w-[700px] lg:max-w-[800px]">
        <div className="p-6 pb-0">
          <DialogHeader>
            <DialogTitle>创建分类任务</DialogTitle>
            <DialogDescription>
              上传文本文件并设置分类规则，系统将根据规则自动对文本进行分类。
            </DialogDescription>
          </DialogHeader>
        </div>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-6 p-6">
            {/* 文件上传 */}
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
                    支持 CSV、Excel 格式，文件大小不超过 10MB
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 分类要求 */}
            <FormField
              control={form.control}
              name="context"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>分类要求</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="请输入具体的分类要求，例如：根据文本内容对客户反馈进行分类..."
                      className="h-24 resize-none"
                      disabled={uploading}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    明确的分类要求有助于系统更准确地进行分类
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 分类规则 */}
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <Label>分类规则</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addCategory}
                  disabled={uploading}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  添加类别
                </Button>
              </div>

              {form.watch('categories').map((_, index) => (
                <div key={index} className="grid grid-cols-12 gap-4">
                  <FormField
                    control={form.control}
                    name={`categories.${index}.name`}
                    render={({ field }) => (
                      <FormItem className="col-span-4">
                        <FormControl>
                          <Input
                            placeholder="类别名称"
                            disabled={uploading}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`categories.${index}.description`}
                    render={({ field }) => (
                      <FormItem className="col-span-7">
                        <FormControl>
                          <Input
                            placeholder="类别描述"
                            disabled={uploading}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="col-span-1 flex items-center">
                    {index >= 2 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeCategory(index)}
                        disabled={uploading}
                      >
                        <Minus className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* 多标签分类开关 */}
            <FormField
              control={form.control}
              name="is_multi_label"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">多标签分类</FormLabel>
                    <FormDescription>
                      启用后，一个文本可以同时属于多个类别
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      disabled={uploading}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            {/* 上传进度条 */}
            {uploading && progress > 0 && (
              <div className="space-y-2">
                <Progress value={progress} />
                <p className="text-sm text-muted-foreground text-center">
                  {progress}%
                </p>
              </div>
            )}

            {/* 操作按钮 */}
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
                    开始分类
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