'use client';

import { useState, useEffect } from 'react';
import { cn } from "@/lib/utils";
import { useVectorData } from '@/hooks/features/feature-config/useVectorData';
import { CollectionConfig } from '@/types/table-manager';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Upload } from 'lucide-react';
import * as XLSX from 'xlsx';
import Papa from 'papaparse';
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
import { Input } from "@/components/ui/input";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info } from "lucide-react";

interface DataUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collection: CollectionConfig;
  database: string;
  editData?: Record<string, any> | null;
  onSuccess?: () => void;
}

type UpdateStrategy = 'upsert' | 'skip' | 'error';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  className?: string;
}

function FileInput({ className, ...props }: InputProps) {
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
  database,
  editData,
  onSuccess
}: DataUploadDialogProps) {
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<Record<string, any>[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [updateStrategy, setUpdateStrategy] = useState<UpdateStrategy>('upsert');
  const [singleRecord, setSingleRecord] = useState<Record<string, any>>({});

  const { batchInsert } = useVectorData({
    database,
    collection
  });

  // 当编辑数据变化时，更新表单
  useEffect(() => {
    if (editData) {
      setSingleRecord(editData);
    } else {
      setSingleRecord({});
    }
  }, [editData]);

  // 解析文件内容
  const parseFileContent = async (file: File): Promise<{ data: any[], columns: string[] }> => {
    if (file.name.endsWith('.csv')) {
      return new Promise((resolve, reject) => {
        Papa.parse(file, {
          header: true,
          complete: (results) => {
            const columns = results.meta.fields || [];
            resolve({ data: results.data, columns });
          },
          error: reject
        });
      });
    } else if (file.name.match(/\.(xlsx|xls)$/)) {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer);
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
      const data = XLSX.utils.sheet_to_json(firstSheet);
      const columns = Object.keys(data[0] || {});
      return { data, columns };
    }
    throw new Error('不支持的文件格式');
  };

  // 验证文件列名是否与配置匹配
  const validateColumns = (columns: string[]): string | null => {
    const requiredFields = collection.fields.map(field => field.name);
    const missingFields = requiredFields.filter(field => !columns.includes(field));
    const extraFields = columns.filter(col => !requiredFields.includes(col));

    if (missingFields.length > 0) {
      return `缺少必需字段: ${missingFields.join(', ')}`;
    }
    if (extraFields.length > 0) {
      return `文件包含未定义字段: ${extraFields.join(', ')}`;
    }
    return null;
  };

  // 处理文件选择
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    try {
      // 验证文件类型
      if (!selectedFile.name.match(/\.(csv|xlsx|xls)$/)) {
        toast({
          variant: "destructive",
          title: "文件格式错误",
          description: "请上传 CSV 或 Excel 格式的文件",
        });
        return;
      }

      setFile(selectedFile);

      // 解析文件
      const { data, columns } = await parseFileContent(selectedFile);

      // 验证列名
      const error = validateColumns(columns);
      if (error) {
        toast({
          variant: "destructive",
          title: "文件格式错误",
          description: error,
        });
        setFile(null);
        return;
      }

      // 预览数据
      setPreviewData(data.slice(0, 10));
    } catch (error) {
      console.error('File processing error:', error);
      toast({
        variant: "destructive",
        title: "文件处理错误",
        description: error instanceof Error ? error.message : "处理文件时发生错误",
      });
      setFile(null);
      setPreviewData(null);
    }
  };

  // 处理单条数据字段变更
  const handleFieldChange = (fieldName: string, value: string) => {
    setSingleRecord(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  // 验证单条数据
  const validateSingleRecord = (): string | null => {
    const requiredFields = collection.fields.map(field => field.name);
    const missingFields = requiredFields.filter(field => !singleRecord[field]);

    if (missingFields.length > 0) {
      return `缺少必需字段: ${missingFields.join(', ')}`;
    }
    return null;
  };

  // 处理单条数据提交
  const handleSingleRecordSubmit = async () => {
    const error = validateSingleRecord();
    if (error) {
      toast({
        variant: "destructive",
        title: "数据验证失败",
        description: error,
      });
      return;
    }

    try {
      setLoading(true);
      const result = await batchInsert([singleRecord], updateStrategy);

      if (result.error_count > 0) {
        toast({
          variant: "destructive",
          title: "保存失败",
          description: result.errors?.[0]?.error || "请检查数据格式是否正确",
        });
      } else {
        toast({
          title: "保存成功",
          description: "数据已保存",
        });
        setSingleRecord({});
        onSuccess?.();
        onOpenChange(false);
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "保存失败",
        description: error instanceof Error ? error.message : "请稍后重试",
      });
    } finally {
      setLoading(false);
    }
  };

  // 处理文件数据上传
  const handleFileUpload = async () => {
    if (!file || !previewData) return;

    try {
      setLoading(true);

      // 解析完整文件
      const { data } = await parseFileContent(file);

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
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editData ? '修改数据' : '导入数据'}</DialogTitle>
          <DialogDescription>
            {editData ? (
              '修改数据记录'
            ) : (
              `导入数据到 ${database} 数据库的 ${collection.display_name || collection.name} Collection。`
            )}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue={editData ? "single" : "file"} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="single">单条数据</TabsTrigger>
            <TabsTrigger value="file" disabled={!!editData}>文件导入</TabsTrigger>
          </TabsList>

          <TabsContent value="single" className="mt-4 space-y-6">
            {/* 字段说明 */}
            <Alert>
              <AlertDescription>
                <div className="space-y-2">
                  <div className="font-medium">系统定义的字段：</div>
                  <div className="grid gap-2 text-sm">
                    {collection.fields.map(field => (
                      <div key={field.name} className="flex items-start gap-2">
                        <span className="font-mono bg-muted px-1.5 py-0.5 rounded-md">
                          {field.name}
                        </span>
                        <span className="text-muted-foreground">
                          {field.description}
                          {field.is_vector && (
                            <span className="ml-1 text-blue-500">(将被自动向量化)</span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </AlertDescription>
            </Alert>

            {/* 单条数据表单 */}
            <div className="space-y-6">
              {/* 更新策略 - 仅在新建时显示 */}
              {!editData && (
                <div className="space-y-2">
                  <Label>更新策略</Label>
                  <Select
                    value={updateStrategy}
                    onValueChange={(value: UpdateStrategy) => setUpdateStrategy(value)}
                  >
                    <SelectTrigger className="w-full sm:w-[200px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="upsert">更新或插入</SelectItem>
                      <SelectItem value="skip">跳过已存在</SelectItem>
                      <SelectItem value="error">遇重复报错</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* 字段输入区域 */}
              <div className="space-y-4">
                {collection.fields.map(field => {
                  const isVectorField = field.is_vector;
                  const isEditMode = !!editData;
                  const isDisabled = isEditMode && isVectorField;

                  return (
                    <div key={field.name} className="space-y-2">
                      <Label className="flex items-center gap-2">
                        <span>{field.description || field.name}</span>
                        {isVectorField && (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <div className="flex items-center">
                                  <span className="text-xs text-blue-500 font-normal">
                                    (将被自动向量化)
                                  </span>
                                  {isEditMode && (
                                    <Info className="h-4 w-4 ml-1 text-blue-500" />
                                  )}
                                </div>
                              </TooltipTrigger>
                              {isEditMode && (
                                <TooltipContent>
                                  <p>向量化字段在编辑模式下不可修改。</p>
                                  <p>如需修改，请删除此记录后重新创建。</p>
                                </TooltipContent>
                              )}
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </Label>
                      <Input
                        value={singleRecord[field.name] || ''}
                        onChange={(e) => handleFieldChange(field.name, e.target.value)}
                        placeholder={`请输入${field.description || field.name}`}
                        disabled={isDisabled}
                        className={isDisabled ? "bg-muted" : ""}
                      />
                      {isDisabled && (
                        <p className="text-xs text-muted-foreground">
                          向量化字段在编辑模式下不可修改，如需修改请删除此记录后重新创建。
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <DialogFooter>
              <div className="flex flex-col-reverse sm:flex-row gap-2 sm:gap-0">
                <Button
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={loading}
                  className="sm:mr-2"
                >
                  取消
                </Button>
                <Button
                  onClick={handleSingleRecordSubmit}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {editData ? '保存中...' : '导入中...'}
                    </>
                  ) : (
                    editData ? '保存' : '导入'
                  )}
                </Button>
              </div>
            </DialogFooter>
          </TabsContent>

          {/* 文件导入 Tab - 仅在非编辑模式下显示 */}
          {!editData && (
            <TabsContent value="file" className="mt-4 space-y-6">
              {/* 字段说明 */}
              <Alert>
                <AlertDescription>
                  <div className="space-y-2">
                    <div className="font-medium">系统定义的字段：</div>
                    <div className="grid gap-2 text-sm">
                      {collection.fields.map(field => (
                        <div key={field.name} className="flex items-start gap-2">
                          <span className="font-mono bg-muted px-1.5 py-0.5 rounded-md">
                            {field.name}
                          </span>
                          <span className="text-muted-foreground">
                            {field.description}
                            {field.is_vector && (
                              <span className="ml-1 text-blue-500">(将被自动向量化)</span>
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </AlertDescription>
              </Alert>

              <div className="space-y-6">
                {/* 更新策略 */}
                <div className="space-y-2">
                  <Label>更新策略</Label>
                  <Select
                    value={updateStrategy}
                    onValueChange={(value: UpdateStrategy) => setUpdateStrategy(value)}
                  >
                    <SelectTrigger className="w-full sm:w-[200px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="upsert">更新或插入</SelectItem>
                      <SelectItem value="skip">跳过已存在</SelectItem>
                      <SelectItem value="error">遇重复报错</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* 文件上传区域 */}
                <div className="space-y-2">
                  <Label>选择文件</Label>
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                    <FileInput
                      type="file"
                      accept=".csv,.xlsx,.xls"
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
                      <span className="text-sm text-muted-foreground break-all">
                        已选择: {file.name}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* 数据预览 */}
              {previewData && (
                <div className="space-y-2">
                  <Label>数据预览（前10条）</Label>
                  <div className="rounded-md border overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {collection.fields.map(field => (
                            <TableHead key={field.name} className="whitespace-nowrap">
                              {field.description || field.name}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {previewData.map((row, index) => (
                          <TableRow key={index}>
                            {collection.fields.map(field => (
                              <TableCell key={field.name} className="truncate max-w-[200px]">
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

              <DialogFooter>
                <div className="flex flex-col-reverse sm:flex-row gap-2 sm:gap-0">
                  <Button
                    variant="outline"
                    onClick={() => onOpenChange(false)}
                    disabled={loading}
                    className="sm:mr-2"
                  >
                    取消
                  </Button>
                  <Button
                    onClick={handleFileUpload}
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
                </div>
              </DialogFooter>
            </TabsContent>
          )}
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}