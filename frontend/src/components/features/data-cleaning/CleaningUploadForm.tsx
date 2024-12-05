import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { useCleaningTaskList } from '@/hooks/features/data-cleaning/useCleaningTaskList';
import { EntityConfigResponse } from '@/types/data-cleaning';

const uploadFormSchema = z.object({
  file: z.custom<File>((v) => v instanceof File, {
    message: '请选择文件',
  }),
  entity_type: z.string({
    required_error: '请选择实体类型',
  }),
  search_enabled: z.boolean().default(true),
  retrieval_enabled: z.boolean().default(true),
});

type UploadFormValues = z.infer<typeof uploadFormSchema>;

interface CleaningUploadFormProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSuccess?: () => void;
  entityTypes: EntityConfigResponse[];
}

export function CleaningUploadForm({
  open,
  onOpenChange,
  onSuccess,
  entityTypes
}: CleaningUploadFormProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const { toast } = useToast();
  const { createTask } = useCleaningTaskList();

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadFormSchema),
    defaultValues: {
      search_enabled: true,
      retrieval_enabled: true,
    }
  });

  const onSubmit = async (data: UploadFormValues) => {
    try {
      setUploading(true);
      setProgress(0);

      await createTask(data.file, data.entity_type, {
        search_enabled: data.search_enabled,
        retrieval_enabled: data.retrieval_enabled,
      });

      toast({
        title: '创建成功',
        description: '数据清洗任务已开始处理',
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

  // 查找当前选中实体类型的配置信息
  const selectedEntityType = entityTypes.find(
    type => type.entity_type === form.watch('entity_type')
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden p-0 md:max-w-[700px] lg:max-w-[800px]">
        <div className="p-6 pb-0">
          <DialogHeader>
            <DialogTitle>创建清洗任务</DialogTitle>
            <DialogDescription>
              上传待清洗的数据文件，选择实体类型并配置清洗选项，系统将自动进行数据清洗和标准化。
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
                    支持 CSV、Excel 格式，文件大小不超过 10MB
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="entity_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>实体类型</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                    disabled={uploading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="选择要清洗的实体类型" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {entityTypes.map((type) => (
                        <SelectItem
                          key={type.entity_type}
                          value={type.entity_type}
                        >
                          {type.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    {selectedEntityType?.description || '请选择要处理的实体类型'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="space-y-4">
              <FormField
                control={form.control}
                name="search_enabled"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">启用网络搜索</FormLabel>
                      <FormDescription>
                        通过网络搜索帮助识别和确认实体信息
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

              <FormField
                control={form.control}
                name="retrieval_enabled"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">启用实体检索</FormLabel>
                      <FormDescription>
                        从已有数据中检索和匹配相似实体
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
            </div>

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
                    开始清洗
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