'use client';

import { FileUploader } from '@/components/features/basic-datalab/FileUploader';
import { AnalysisInput } from '@/components/features/basic-datalab/AnalysisInput';
import { ExecutionResult } from '@/components/features/basic-datalab/ExecutionResult';
import { useBasicDatalab } from '@/hooks/features/basic-datalab/useBasicDatalab';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from 'react';

export default function BasicDatalabPage() {
  const {
    uploadedFiles,
    analyzing,
    executing,
    pyodideReady,
    analysisResult,
    handleFileUpload,
    handleFileDelete,
    executeAnalysis,
  } = useBasicDatalab();

  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="flex-1 space-y-8 p-4 md:p-8 pt-6">
      {/* 标题区域 */}
      <div className="border-b pb-6">
        <div className="container px-0">
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div className="space-y-3">
              <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground/90">
                基础数据工坊
              </h1>
              <p className="text-sm md:text-base text-muted-foreground max-w-3xl">
                上传数据并描述您的处理需求，系统将协助您完成基础的数据处理与分析。
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="space-y-8">
        {/* 可折叠的文件上传区域 */}
        <Collapsible open={isOpen} onOpenChange={setIsOpen} className="border rounded-lg">
          <CollapsibleTrigger asChild>
            <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-secondary/10 transition-colors">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-medium">数据文件</h2>
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
                <div className="flex items-center gap-2 min-w-0">
                  {uploadedFiles.length > 0 ? (
                    <>
                      <span className="bg-secondary px-2 py-0.5 rounded-full text-xs">
                        {uploadedFiles.length} 个文件
                      </span>
                      <span className="text-sm text-muted-foreground truncate">
                        {uploadedFiles.map(f => f.name).join(', ')}
                      </span>
                    </>
                  ) : (
                    <span className="text-sm text-muted-foreground">暂无数据文件</span>
                  )}
                </div>
              </div>
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="border-t p-4">
              <FileUploader
                files={uploadedFiles}
                onUpload={handleFileUpload}
                onDelete={handleFileDelete}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* 分析输入区域 */}
        <AnalysisInput
          onSubmit={executeAnalysis}
          disabled={!pyodideReady || uploadedFiles.length === 0}
          analyzing={analyzing}
        />

        {/* 执行结果区域 */}
        <ExecutionResult
          result={analysisResult}
          executing={executing}
        />
      </div>
    </div>
  );
}