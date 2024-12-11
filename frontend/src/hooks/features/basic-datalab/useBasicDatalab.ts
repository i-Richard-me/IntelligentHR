import { useState, useEffect, useCallback, useRef } from 'react';
import { basicDatalabApi } from '@/services';
import { useToast } from '@/hooks/use-toast';
import type {
  UploadedFileInfo,
  AnalysisResult,
  AssistantResponse
} from '@/types/basic-datalab';

interface PyodideInterface {
  loadPyodide: any;
  runPythonAsync: (code: string) => Promise<any>;
  loadPackagesFromImports: (code: string) => Promise<void>;
  loadPackage: (packages: string[] | string) => Promise<void>;
  globals: any;
  FS: any;
}

interface PyodideLoadOptions {
  indexURL: string;
  fullStdLib?: boolean;
}

declare global {
  interface Window {
    loadPyodide: (options: PyodideLoadOptions) => Promise<PyodideInterface>;
    pyodide: PyodideInterface | null;
  }
}

const PYODIDE_CDN_URL = "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/";

interface PendingFile {
  file: File;
  content: ArrayBuffer;
}

export function useBasicDatalab() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileInfo[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [pyodideReady, setPyodideReady] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const { toast } = useToast();

  // 使用 ref 来存储待处理的文件
  const pendingFiles = useRef<Record<string, PendingFile>>({});

  // 初始化 Pyodide
  useEffect(() => {
    let mounted = true;

    const initializePyodide = async () => {
      if (window.pyodide) {
        setPyodideReady(true);
        return;
      }

      try {
        if (!document.querySelector('script[src*="pyodide.js"]')) {
          const preloadLink = document.createElement('link');
          preloadLink.rel = 'preload';
          preloadLink.as = 'script';
          preloadLink.href = `${PYODIDE_CDN_URL}pyodide.js`;
          document.head.appendChild(preloadLink);

          const script = document.createElement('script');
          script.src = `${PYODIDE_CDN_URL}pyodide.js`;
          script.crossOrigin = 'anonymous';
          script.setAttribute('data-cache-max-age', '604800');
          document.body.appendChild(script);

          await new Promise((resolve, reject) => {
            script.onload = resolve;
            script.onerror = reject;
          });
        }

        window.pyodide = await window.loadPyodide({
          indexURL: PYODIDE_CDN_URL,
          fullStdLib: false,
        });

        await window.pyodide.loadPackage(['pandas', 'numpy', 'matplotlib']);

        await window.pyodide.runPythonAsync(`
          import sys
          import io
          import pandas as pd
          import numpy as np
          import matplotlib
          matplotlib.use('agg')
          import matplotlib.pyplot as plt
          
          plt.style.use('seaborn')
          matplotlib.rcParams['figure.figsize'] = (10, 6)
          matplotlib.rcParams['figure.dpi'] = 100
        `);

        // Pyodide 准备就绪后，处理所有待处理的文件
        if (Object.keys(pendingFiles.current).length > 0) {
          for (const [fileName, { content }] of Object.entries(pendingFiles.current)) {
            window.pyodide.FS.writeFile(
              fileName,
              new Uint8Array(content)
            );
          }
          // 清空待处理文件
          pendingFiles.current = {};
        }

        if (mounted) {
          setPyodideReady(true);
        }
      } catch (error) {
        console.error('Pyodide initialization error:', error);
      }
    };

    initializePyodide();

    return () => {
      mounted = false;
    };
  }, []);

  // 处理文件上传
  const handleFileUpload = useCallback(async (files: FileList) => {
    try {
      const newFiles: UploadedFileInfo[] = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!file.name.toLowerCase().endsWith('.csv')) {
          throw new Error('只支持CSV文件格式');
        }

        if (file.size > 10 * 1024 * 1024) {
          throw new Error('文件大小不能超过10MB');
        }

        // 获取文件的数据类型信息
        const dtypes = await basicDatalabApi.inferDtypes(file);

        // 读取文件内容
        const content = await file.arrayBuffer();

        // 如果 Pyodide 已经准备好，直接写入文件系统
        if (window.pyodide?.FS) {
          window.pyodide.FS.writeFile(
            file.name,
            new Uint8Array(content)
          );
        } else {
          // 否则将文件存储在待处理队列中
          pendingFiles.current[file.name] = {
            file,
            content
          };
        }

        newFiles.push({
          name: file.name,
          size: file.size,
          type: file.type,
          dtypes,
          uploadedAt: new Date()
        });
      }

      setUploadedFiles(prev => [...prev, ...newFiles]);

      if (newFiles.length > 0) {
        toast({
          title: "文件已就绪",
          description: `已上传 ${newFiles.length} 个文件，可以开始分析`,
        });
      }
    } catch (error) {
      console.error('File upload error:', error);
      toast({
        variant: "destructive",
        title: "上传失败",
        description: error instanceof Error ? error.message : "文件上传失败"
      });
    }
  }, [toast]);

  // 删除文件
  const handleFileDelete = useCallback((fileName: string) => {
    try {
      if (window.pyodide?.FS) {
        window.pyodide.FS.unlink(fileName);
      }
      setUploadedFiles(prev => prev.filter(file => file.name !== fileName));
    } catch (error) {
      console.error('File deletion error:', error);
      toast({
        variant: "destructive",
        title: "删除失败",
        description: "文件删除失败，请重试"
      });
    }
  }, [toast]);

  // 执行分析
  const executeAnalysis = useCallback(async (userInput: string) => {
    if (!window.pyodide) {
      toast({
        variant: "destructive",
        title: "系统未就绪",
        description: "请稍后再试"
      });
      return;
    }

    if (uploadedFiles.length === 0) {
      toast({
        variant: "destructive",
        title: "未上传文件",
        description: "请先上传要分析的CSV文件"
      });
      return;
    }

    try {
      setAnalyzing(true);
      setAnalysisResult(null);

      // 准备请求数据
      const tableInfo = uploadedFiles.reduce((acc, file) => {
        acc[file.name] = { dtypes: file.dtypes };
        return acc;
      }, {} as Record<string, { dtypes: Record<string, string> }>);

      // 调用后端API获取Python代码
      const response = await basicDatalabApi.analyze({
        user_input: userInput,
        table_info: tableInfo
      });

      if (response.error) {
        throw new Error(response.error.detail);
      }

      const result = response.data;

      // 处理需要更多信息的情况
      if (result.next_step === 'need_more_info') {
        setAnalysisResult({
          status: 'need_more_info',
          message: result.message
        });
        return;
      }

      // 处理超出范围的情况
      if (result.next_step === 'out_of_scope') {
        setAnalysisResult({
          status: 'out_of_scope',
          message: result.message
        });
        return;
      }

      if (!result.command?.code) {
        throw new Error('系统无法生成分析代码');
      }

      // 执行Python代码
      setExecuting(true);
      let output = '';
      let chartData: string | undefined;
      let outputFile: AnalysisResult['outputFile'] | undefined;

      try {
        // 设置输出捕获
        await window.pyodide.runPythonAsync(`
          import io
          import sys
          _stdout = sys.stdout
          _stderr = sys.stderr
          sys.stdout = io.StringIO()
          sys.stderr = io.StringIO()
        `);

        // 执行代码
        await window.pyodide.runPythonAsync(result.command.code);

        // 获取输出
        const stdout = await window.pyodide.runPythonAsync('sys.stdout.getvalue()');
        const stderr = await window.pyodide.runPythonAsync('sys.stderr.getvalue()');
        output = stdout + stderr;

        // 检查是否有图表输出
        const hasFigure = await window.pyodide.runPythonAsync('plt.get_fignums()');
        if (hasFigure.length > 0) {
          chartData = await window.pyodide.runPythonAsync(`
            import base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            base64.b64encode(buf.read()).decode('utf-8')
          `);
          await window.pyodide.runPythonAsync('plt.close("all")');
        }

        // 处理输出文件
        if (result.command.output_filename) {
          try {
            const fileContent = window.pyodide.FS.readFile(
              result.command.output_filename,
              { encoding: 'binary' }
            );
            outputFile = {
              filename: result.command.output_filename,
              content: fileContent,
              size: fileContent.length
            };
          } catch (fileError) {
            console.error('Failed to read output file:', fileError);
            output += '\n读取输出文件失败';
          }
        }

        setAnalysisResult({
          status: 'success',
          output,
          chartData,
          outputFile
        });
      } catch (execError) {
        console.error('Code execution error:', execError);
        setAnalysisResult({
          status: 'error',
          output,
          error: execError instanceof Error ? execError.message : '代码执行失败'
        });
      } finally {
        // 恢复标准输出
        await window.pyodide.runPythonAsync(`
          sys.stdout = _stdout
          sys.stderr = _stderr
        `);
      }
    } catch (error) {
      console.error('Analysis error:', error);
      setAnalysisResult({
        status: 'error',
        error: error instanceof Error ? error.message : '分析失败，请稍后重试'
      });
    } finally {
      setAnalyzing(false);
      setExecuting(false);
    }
  }, [uploadedFiles, toast]);

  return {
    uploadedFiles,
    analyzing,
    executing,
    pyodideReady,
    analysisResult,
    handleFileUpload,
    handleFileDelete,
    executeAnalysis
  };
}