import { useState, useCallback } from 'react';
import { Loader2, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface AnalysisInputProps {
  onSubmit: (input: string) => Promise<void>;
  disabled?: boolean;
  analyzing?: boolean;
}

export function AnalysisInput({
  onSubmit,
  disabled = false,
  analyzing = false
}: AnalysisInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = useCallback(async () => {
    if (!input.trim()) return;
    await onSubmit(input.trim());
  }, [input, onSubmit]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value.length <= 1000) {
      setInput(value);
    }
  }, []);

  return (
    <div className="space-y-2.5">
      <Label htmlFor="analysis-input" className="text-base font-medium">
        请输入您的处理需求
      </Label>
      <div className="space-y-3">
        <Input
          id="analysis-input"
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="请输入数据处理需求，例如：计算每个城市的平均年龄和人数"
          className="max-w-2xl"
          disabled={disabled || analyzing}
          maxLength={1000}
        />
        <div className="flex items-center gap-3">
          <Button
            onClick={handleSubmit}
            disabled={disabled || analyzing || !input.trim()}
            className="whitespace-nowrap"
          >
            {analyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                处理中
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                开始处理
              </>
            )}
          </Button>
          {input && (
            <span className="text-sm text-muted-foreground">
              {input.length}/1000
            </span>
          )}
        </div>
      </div>
    </div>
  );
}