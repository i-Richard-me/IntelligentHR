import { AlertCircle, Terminal, Info, Ban, Download } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import type { AnalysisResult } from '@/types/basic-datalab';

interface ExecutionResultProps {
  result: AnalysisResult | null;
  executing?: boolean;
}

export function ExecutionResult({
  result,
  executing = false
}: ExecutionResultProps) {
  if (!result && !executing) {
    return null;
  }

  // 处理文件下载
  const handleDownload = () => {
    if (!result?.outputFile) return;

    // 创建 Blob 对象
    const blob = new Blob([result.outputFile.content], {
      type: 'text/csv;charset=utf-8;'
    });

    // 创建下载链接
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', result.outputFile.filename);
    document.body.appendChild(link);
    link.click();

    // 清理
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  return (
    <Card className="transition-all duration-200">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base font-medium">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4" />
            分析结果
          </div>
          {result?.outputFile && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              下载结果文件
              <span className="text-xs text-muted-foreground">
                ({(result.outputFile.size / 1024).toFixed(1)} KB)
              </span>
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {executing ? (
          // 加载状态
          <div className="space-y-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/6" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-2/3" />
            </div>
            <Skeleton className="h-[200px] w-full rounded-md" />
          </div>
        ) : result ? (
          <div className="space-y-4">
            {/* 需要更多信息 */}
            {result.status === 'need_more_info' && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  {result.message || '需要更多信息来完成处理，请提供更详细的需求说明。'}
                </AlertDescription>
              </Alert>
            )}

            {/* 超出范围 */}
            {result.status === 'out_of_scope' && (
              <Alert variant="destructive">
                <Ban className="h-4 w-4" />
                <AlertDescription>
                  {result.message || '抱歉，您的需求超出了系统的处理范围。'}
                </AlertDescription>
              </Alert>
            )}

            {/* 错误信息 */}
            {result.status === 'error' && result.error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {result.error}
                </AlertDescription>
              </Alert>
            )}

            {/* 输出内容 */}
            {result.output && (
              <div className="relative">
                <div className="w-full rounded-md border bg-muted/50">
                  <pre className="font-mono text-sm leading-relaxed p-4 whitespace-pre-wrap break-words max-h-[500px] overflow-y-auto">
                    {result.output}
                  </pre>
                </div>
              </div>
            )}

            {/* 图表展示 */}
            {result.chartData && (
              <div className="overflow-hidden rounded-lg border bg-background p-2">
                <img
                  src={`data:image/png;base64,${result.chartData}`}
                  alt="Analysis Chart"
                  className="mx-auto max-h-[500px] w-auto rounded-md object-contain"
                  loading="lazy"
                />
              </div>
            )}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}