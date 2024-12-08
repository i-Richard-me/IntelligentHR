'use client';

import { useFieldArray, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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
import { CollectionConfig, CollectionFieldConfig } from '@/types/table-manager';

// 表单验证规则
const collectionFieldSchema = z.object({
  name: z
    .string()
    .min(1, '请输入字段名称')
    .max(50, '字段名称不能超过50个字符')
    .regex(/^[a-zA-Z][a-zA-Z0-9_]*$/, '字段名称必须以字母开头，只能包含字母、数字和下划线'),
  type: z
    .string()
    .min(1, '请选择字段类型')
    .regex(/^(string|text|int|float|boolean)$/, '无效的字段类型'),
  description: z
    .string()
    .max(200, '字段描述不能超过200个字符')
    .optional()
    .nullable()
    .transform(val => val || undefined), // 将 null 转换为 undefined
  is_vector: z
    .boolean()
    .default(false),
});

const collectionConfigSchema = z.object({
  name: z
    .string()
    .min(1, '请输入Collection名称')
    .max(100, 'Collection名称不能超过100个字符')
    .regex(/^[a-zA-Z][a-zA-Z0-9_]*$/, 'Collection名称必须以字母开头，只能包含字母、数字和下划线'),
  display_name: z
    .string()
    .max(100, '显示名称不能超过100个字符')
    .optional()
    .nullable()
    .transform(val => val || undefined),
  description: z
    .string()
    .max(500, '描述不能超过500个字符')
    .optional()
    .nullable()
    .transform(val => val || undefined),
  fields: z.array(collectionFieldSchema).min(1, '至少需要添加一个字段'),
  collection_databases: z.array(z.string()).min(1, '至少需要选择一个数据库'),
  embedding_fields: z.array(z.string()).default([]),
  feature_modules: z.array(z.string()).default(['data_cleaning']),
});

export type CollectionConfigFormValues = z.infer<typeof collectionConfigSchema>;

interface CollectionConfigDialogProps {
  open?: boolean;
  defaultValues?: Partial<CollectionConfig>;
  onOpenChange?: (open: boolean) => void;
  onSubmit?: (data: CollectionConfigFormValues) => Promise<void>;
}

const FIELD_TYPES = [
  { label: '字符串', value: 'string' },
  { label: '长文本', value: 'text' },
  { label: '整数', value: 'int' },
  { label: '浮点数', value: 'float' },
  { label: '布尔值', value: 'boolean' },
];

const DEFAULT_DATABASES = ['production', 'data_cleaning', 'examples']; // 实际应从后端获取

export function VectorCollectionDialog({
  open,
  defaultValues,
  onOpenChange,
  onSubmit
}: CollectionConfigDialogProps) {
  // 初始化表单
  const form = useForm<CollectionConfigFormValues>({
    resolver: zodResolver(collectionConfigSchema),
    defaultValues: {
      name: '',
      display_name: '',
      description: '',
      fields: [],
      embedding_fields: [],
      collection_databases: [],
      feature_modules: ['data_cleaning'],
      ...defaultValues,
    },
  });

  // 字段列表的动态管理
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "fields",
  });

  // 处理表单提交
  const handleSubmit = async (data: CollectionConfigFormValues) => {
    try {
      // 根据is_vector为true的字段自动设置embedding_fields
      const embeddingFields = data.fields
        .filter(field => field.is_vector)
        .map(field => field.name);
      data.embedding_fields = embeddingFields;

      await onSubmit?.(data);
      form.reset(); // 重置表单
    } catch (error) {
      console.error('Submit error:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {defaultValues ? '编辑Collection配置' : '添加Collection配置'}
          </DialogTitle>
          <DialogDescription>
            配置向量数据库Collection的结构信息和字段定义。所有带 * 的字段为必填项。
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Collection名称 */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Collection名称 *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="example_collection"
                      {...field}
                      disabled={!!defaultValues}
                    />
                  </FormControl>
                  <FormDescription>
                    唯一的Collection标识，创建后不可修改
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
                  <FormLabel>显示名称</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="请输入显示名称"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    用于在界面上展示的友好名称
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
                      placeholder="请输入Collection的用途说明..."
                      className="h-20"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Collection的详细说明，便于其他人理解其用途
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 允许使用的数据库 */}
            <FormField
              control={form.control}
              name="collection_databases"
              render={() => (
                <FormItem>
                  <FormLabel>允许使用的数据库 *</FormLabel>
                  <div className="grid grid-cols-2 gap-4">
                    {DEFAULT_DATABASES.map((db) => (
                      <FormField
                        key={db}
                        control={form.control}
                        name="collection_databases"
                        render={({ field }) => {
                          return (
                            <FormItem className="flex flex-row items-center space-x-3 space-y-0">
                              <FormControl>
                                <Checkbox
                                  checked={field.value?.includes(db)}
                                  onCheckedChange={(checked) => {
                                    return checked
                                      ? field.onChange([...field.value, db])
                                      : field.onChange(
                                          field.value?.filter(
                                            (value) => value !== db
                                          )
                                        )
                                  }}
                                />
                              </FormControl>
                              <FormLabel className="text-sm font-normal">
                                {db}
                              </FormLabel>
                            </FormItem>
                          )
                        }}
                      />
                    ))}
                  </div>
                  <FormDescription>
                    选择可以使用该Collection的数据库
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* 字段列表 */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <FormLabel>字段定义 *</FormLabel>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    append({
                      name: '',
                      type: 'string',
                      description: '',
                      is_vector: false,
                    });
                  }}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  添加字段
                </Button>
              </div>

              {fields.map((field, index) => (
                <div key={field.id} className="space-y-4 rounded-lg border p-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium">字段 {index + 1}</h4>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField
                      control={form.control}
                      name={`fields.${index}.name`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>字段名称 *</FormLabel>
                          <FormControl>
                            <Input placeholder="field_name" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name={`fields.${index}.type`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>字段类型 *</FormLabel>
                          <FormControl>
                            <select
                              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                              {...field}
                            >
                              {FIELD_TYPES.map(type => (
                                <option key={type.value} value={type.value}>
                                  {type.label}
                                </option>
                              ))}
                            </select>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={form.control}
                    name={`fields.${index}.description`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>字段描述</FormLabel>
                        <FormControl>
                          <Input placeholder="字段的用途说明" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name={`fields.${index}.is_vector`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>
                            向量化字段
                          </FormLabel>
                          <FormDescription>
                            是否需要对该字段进行向量化处理
                          </FormDescription>
                        </div>
                      </FormItem>
                    )}
                  />
                </div>
              ))}
              {fields.length === 0 && (
                <div className="text-center text-sm text-muted-foreground py-4">
                  请添加至少一个字段
                </div>
              )}
            </div>

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