import { apiRequest } from './api-client';
import { AnalysisRequest, AnalysisResponse, AssistantResponse } from '@/types/basic-datalab';

export const basicDatalabApi = {
  /**
   * 分析数据并生成Python命令
   */
  analyze: async (data: AnalysisRequest): Promise<AnalysisResponse> => {
    return apiRequest<AssistantResponse>({
      method: 'POST',
      url: '/basic-datalab/analyze',
      data,
    });
  },

  /**
   * 解析CSV文件获取数据类型信息
   * @param file CSV文件
   * @returns 返回文件的列数据类型映射
   */
  inferDtypes: async (file: File): Promise<Record<string, string>> => {
    // 使用 FileReader 读取 CSV 文件的前几行
    const firstChunk = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      // 只读取文件的前8KB来推断类型
      const chunk = file.slice(0, 8192);
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.readAsText(chunk);
    });

    // 简单的CSV解析以获取列名和样本数据
    const lines = firstChunk.split('\n').filter(line => line.trim());
    if (lines.length < 2) {
      throw new Error('文件格式错误或为空');
    }

    const headers = lines[0].split(',').map(h => h.trim());
    const sampleData = lines[1].split(',').map(d => d.trim());

    // 推断每列的数据类型
    const dtypes: Record<string, string> = {};
    headers.forEach((header, index) => {
      const value = sampleData[index];
      // 简单的类型推断逻辑
      if (!isNaN(Number(value))) {
        if (value.includes('.')) {
          dtypes[header] = 'float64';
        } else {
          dtypes[header] = 'int64';
        }
      } else if (value.toLowerCase() === 'true' || value.toLowerCase() === 'false') {
        dtypes[header] = 'bool';
      } else {
        dtypes[header] = 'string';
      }
    });

    return dtypes;
  }
};