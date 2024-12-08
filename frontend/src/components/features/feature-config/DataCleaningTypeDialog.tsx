'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { AnalysisModelConfig } from '@/types/table-manager';

// 表单验证规则
const modelConfigSchema = z.object({
  entity_type: z
    .string()
    .min(1, '请输入模型标识')
    .max(50, '模型标识不能超过50个字符')
    .regex(/^[a-z0-9-_]+$/, '只能使用小写字母、数字、下划线和短横线'),
  display_name: z
    .string()
    .min(1, '请输入显示名称')
    .max(100, '显示名称不能超过100个字符'),
  description: z
    .string()
    .max(500, '描述不能超过500个字符')
    .optional(),
  validation_instructions: z
    .string()
    .min(1, '请输入输入验证指令')
    .max(2000, '输入验证指令不能超过2000个字符'),
  analysis_instructions: z
    .string()
    .min(1, '请输入分析指令')
    .max(2000, '分析指令不能超过2000个字符'),
  verification_instructions: z
    .string()
    .min(1, '请输入验证指令')
    .max(2000, '验证指令不能超过2000个字符'),
  collection_name: z
    .string()
    .min(1, '请输入集合名称')
    .max(100, '集合名称不能超过100个字符')
    .regex(/^[a-zA-Z0-9_]+$/, '只能使用字母、数字和下划线'),
});

type ModelConfigFormValues = z.infer<typeof modelConfigSchema>;

interface ModelConfigDialogProps {
  open?: boolean;
  defaultValues?: Partial<AnalysisModelConfig>;
  onOpenChange?: (open: boolean) => void;
  onSubmit?: (data: ModelConfigFormValues) => Promise<void>;
}

export function DataCleaningTypeDialog({
  open,
  defaultValues,
  onOpenChange,
  onSubmit
}: ModelConfigDialogProps) {
  // 初始化表单
  const form = useForm<ModelConfigFormValues>({
    resolver: zodResolver(modelConfigSchema),
    defaultValues: {
      entity_type: '',
      display_name: '',
      description: '',
      validation_instructions: '',
      analysis_instructions: '',
      verification_instructions: '',
      collection_name: '',
      ...defaultValues,
    },
  });

  // 处理表单提交
  const handleSubmit = async (data: ModelConfigFormValues) => {
    try {
      await onSubmit?.(data);
      form.reset(); // 重置表单
    } catch (error) {
      // 错误已在父组件处理
      console.error('Submit error:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {defaultValues ? '编辑业务分析模型' : '添加业务分析模型'}
          </DialogTitle>
          <DialogDescription>
            配置业务分析模型的基本信息和分析规则。所有带 * 的字段为必填项。
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* 模型标识 */}
            <FormField
              control={form.control}
              name="entity_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>模型标识 *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="company-name"
                      {...field}
                      disabled={!!defaultValues}
                    />
                  </FormControl>
                  <FormDescription>
                    唯一的模型标识，用于系统内部识别，创建后不可修改
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 显示名称 */}
            <FormField
              control={form.control}
              name="display_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>显示名称 *</FormLabel>
                  <FormControl>
                    <Input placeholder="公司名称" {...field} />
                  </FormControl>
                  <FormDescription>
                    在用户界面显示的模型名称
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 描述 */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>描述</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="输入模型的详细说明..."
                      className="h-20"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    对这个业务分析模型的详细说明
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 输入验证指令 */}
            <FormField
              control={form.control}
              name="validation_instructions"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>输入验证指令 *</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="输入用于验证用户输入是否有效的指令..."
                      className="h-32"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    用于验证用户输入是否为有效的分析对象
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 分析指令 */}
            <FormField
              control={form.control}
              name="analysis_instructions"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>分析指令 *</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="输入用于分析和识别实体的指令..."
                      className="h-32"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    用于从搜索结果中分析和识别标准实体名称
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 验证指令 */}
            <FormField
              control={form.control}
              name="verification_instructions"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>验证指令 *</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="输入用于验证分析结果的指令..."
                      className="h-32"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    用于验证分析结果是否准确
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 集合名称 */}
            <FormField
              control={form.control}
              name="collection_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>集合名称 *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="company_names"
                      {...field}
                      disabled={!!defaultValues}
                    />
                  </FormControl>
                  <FormDescription>
                    存储标准化数据的向量数据库集合名称，创建后不可修改
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange?.(false)}
              >
                取消
              </Button>
              <Button
                type="submit"
                disabled={form.formState.isSubmitting}
              >
                {form.formState.isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    保存中...
                  </>
                ) : (
                  '保存'
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}