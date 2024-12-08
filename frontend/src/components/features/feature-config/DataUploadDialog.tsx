'use client';

import { useState, useCallback } from 'react';
import { cn } from "@/lib/utils";
import { useCollectionData } from '@/hooks/features/feature-config/useCollectionData';
import { CollectionConfig } from '@/types/table-manager';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Upload } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface DataUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collection: CollectionConfig;
  database: string;  // 新增的数据库参数
  onSuccess?: () => void;
}

type UpdateStrategy = 'upsert' | 'skip' | 'error';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  className?: string;
}

function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  );
}

export function DataUploadDialog({
  open,
  onOpenChange,
  collection,
  database,  // 添加到参数列表
  onSuccess
}: DataUploadDialogProps) {
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<Record<string, any>[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [updateStrategy, setUpdateStrategy] = useState<UpdateStrategy>('upsert');

  // 使用 database 参数初始化 hook
  const { batchInsert } = useCollectionData({
    collection,
    database  // 传递数据库参数
  });

  // 处理文件选择
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    try {
      // 验证文件类型
      if (!selectedFile.name.endsWith('.json')) {
        toast({
          variant: "destructive",
          title: "文件格式错误",
          description: "请上传JSON格式的文件",
        });
        return;
      }

      setFile(selectedFile);

      // 读取文件预览
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const content = JSON.parse(e.target?.result as string);
          // 验证数据格式
          if (!Array.isArray(content)) {
            throw new Error('数据必须是数组格式');
          }

          // 预览前10条数据
          setPreviewData(content.slice(0, 10));
        } catch (error) {
          toast({
            variant: "destructive",
            title: "数据格式错误",
            description: "请上传有效的JSON数组数据",
          });
          setFile(null);
          setPreviewData(null);
        }
      };
      reader.readAsText(selectedFile);
    } catch (error) {
      console.error('File processing error:', error);
      toast({
        variant: "destructive",
        title: "文件处理错误",
        description: "处理文件时发生错误",
      });
    }
  };

  // 验证数据字段
  const validateData = (data: Record<string, any>[]) => {
    const requiredFields = collection.fields
      .filter(field => !field.is_vector)
      .map(field => field.name);

    for (const record of data) {
      for (const field of requiredFields) {
        if (!(field in record)) {
          return `缺少必需字段: ${field}`;
        }
      }
    }
    return null;
  };

  // 处理数据上传
  const handleUpload = async () => {
    if (!file || !previewData) return;

    try {
      setLoading(true);

      // 读取完整文件内容
      const reader = new FileReader();
      const fileContent = await new Promise<string>((resolve, reject) => {
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = reject;
        reader.readAsText(file);
      });

      const data = JSON.parse(fileContent);

      // 验证数据格式
      const error = validateData(data);
      if (error) {
        toast({
          variant: "destructive",
          title: "数据格式错误",
          description: error,
        });
        return;
      }

      // 上传数据
      const result = await batchInsert(data, updateStrategy);

      if (result.error_count > 0) {
        toast({
          variant: "destructive",
          title: "部分数据导入失败",
          description: `成功: ${result.success_count} 条，失败: ${result.error_count} 条`,
        });
      } else {
        toast({
          title: "导入成功",
          description: `成功导入 ${result.success_count} 条数据`,
        });
      }

      // 重置状态
      setFile(null);
      setPreviewData(null);
      onSuccess?.();
      onOpenChange(false);
    } catch (error) {
      console.error('Upload error:', error);
      toast({
        variant: "destructive",
        title: "上传失败",
        description: error instanceof Error ? error.message : "导入数据时发生错误",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>导入数据</DialogTitle>
          <DialogDescription>
            导入数据到 {database} 数据库的 {collection.display_name || collection.name} Collection。
            请上传JSON格式的数据文件，数据必须是对象数组格式。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* 文件上传区域 */}
          <div className="space-y-4">
            <Label>选择文件</Label>
            <div className="flex items-center gap-4">
              <Input
                type="file"
                accept=".json"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
              />
              <Label
                htmlFor="file-upload"
                className="cursor-pointer inline-flex h-10 items-center justify-center whitespace-nowrap rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground ring-offset-background transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <Upload className="mr-2 h-4 w-4" />
                选择文件
              </Label>
              {file && (
                <span className="text-sm text-muted-foreground">
                  已选择: {file.name}
                </span>
              )}
            </div>
          </div>

          {/* 更新策略 */}
          <div className="space-y-4">
            <Label>更新策略</Label>
            <Select
              value={updateStrategy}
              onValueChange={(value: UpdateStrategy) => setUpdateStrategy(value)}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="upsert">更新或插入</SelectItem>
                <SelectItem value="skip">跳过已存在</SelectItem>
                <SelectItem value="error">遇重复报错</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 字段说明 */}
          <Alert>
            <AlertDescription>
              <span className="font-medium">必填字段：</span>
              {collection.fields
                .filter(field => !field.is_vector)
                .map(field => field.name)
                .join(', ')}
            </AlertDescription>
          </Alert>

          {/* 数据预览 */}
          {previewData && (
            <div className="space-y-4">
              <Label>数据预览（前10条）</Label>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {collection.fields
                        .filter(field => !field.is_vector)
                        .map(field => (
                          <TableHead key={field.name}>
                            {field.description || field.name}
                          </TableHead>
                        ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {previewData.map((row, index) => (
                      <TableRow key={index}>
                        {collection.fields
                          .filter(field => !field.is_vector)
                          .map(field => (
                            <TableCell key={field.name}>
                              {String(row[field.name] ?? '-')}
                            </TableCell>
                          ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="mt-6">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            取消
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!file || loading}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                导入中...
              </>
            ) : (
              '开始导入'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}