import { useRef, useCallback } from 'react';
import { X, Upload, FileText, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Badge } from "@/components/ui/badge"
import type { UploadedFileInfo } from '@/types/basic-datalab';
import { useState } from 'react';

interface FileUploaderProps {
  files: UploadedFileInfo[];
  onUpload: (files: FileList) => Promise<void>;
  onDelete: (fileName: string) => void;
}

export function FileUploader({
  files,
  onUpload,
  onDelete,
}: FileUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [openFileDetails, setOpenFileDetails] = useState<Record<string, boolean>>({});

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      onUpload(files);
      event.target.value = '';
    }
  }, [onUpload]);

  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const toggleFileDetails = useCallback((fileName: string) => {
    setOpenFileDetails(prev => ({
      ...prev,
      [fileName]: !prev[fileName]
    }));
  }, []);

  const toggleAllFileDetails = useCallback(() => {
    const allExpanded = files.every(file => openFileDetails[file.name]);
    const newState = files.reduce((acc, file) => ({
      ...acc,
      [file.name]: !allExpanded
    }), {});
    setOpenFileDetails(newState);
  }, [files, openFileDetails]);

  const allExpanded = files.length > 0 && files.every(file => openFileDetails[file.name]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        {files.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleAllFileDetails}
            className="gap-2"
          >
            {allExpanded ? (
              <>
                <ChevronUp className="h-4 w-4" />
                隐藏字段信息
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4" />
                查看字段信息
              </>
            )}
          </Button>
        )}
        <div className="flex items-center gap-2 ml-auto">
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".csv"
            multiple
            onChange={handleFileSelect}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleUploadClick}
          >
            <Upload className="mr-2 h-4 w-4" />
            选择文件
          </Button>
        </div>
      </div>

      {files.length === 0 ? (
        // 未上传文件时显示提示
        <div className="flex justify-center rounded-lg border border-dashed border-gray-200 px-6 py-8">
          <div className="text-center text-sm text-muted-foreground">
            <FileText className="mx-auto h-8 w-8" />
            <p className="mt-2">支持上传 CSV 文件，每个文件大小不超过 10MB</p>
          </div>
        </div>
      ) : (
        // 文件列表
        <div className="space-y-2">
          {files.map((file) => (
            <Collapsible
              key={file.name}
              open={openFileDetails[file.name]}
              onOpenChange={() => toggleFileDetails(file.name)}
            >
              <div className="rounded-md border border-gray-200">
                <div className="flex items-center justify-between p-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="h-5 w-5 flex-shrink-0 text-gray-400" />
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">
                          {file.name}
                        </span>
                        {Object.keys(file.dtypes).length > 15 && (
                          <div className="flex items-center gap-1.5 text-yellow-600 bg-yellow-50 px-2 py-0.5 rounded-full text-xs">
                            <AlertCircle className="h-3.5 w-3.5" />
                            <span>字段数量较多，可影响分析效果</span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{(file.size / 1024).toFixed(1)} KB</span>
                        <span>•</span>
                        <span>{Object.keys(file.dtypes).length} 列</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <CollapsibleTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        {openFileDetails[file.name] ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                    </CollapsibleTrigger>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => onDelete(file.name)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <CollapsibleContent>
                  <div className="border-t border-gray-100 bg-gray-50/50 p-3">
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(file.dtypes).map(([column, type]) => (
                        <Badge
                          key={column}
                          variant="secondary"
                          className="cursor-default"
                        >
                          {column}: {type}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CollapsibleContent>
              </div>
            </Collapsible>
          ))}
        </div>
      )}
    </div>
  );
}