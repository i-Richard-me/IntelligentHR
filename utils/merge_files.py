import os
import re

def merge_python_files(directory: str, output_file: str):
    """
    合并目录下所有Python文件到单个文件
    
    Args:
        directory: 源代码目录路径
        output_file: 输出文件路径
    """
    # 存储所有找到的Python文件
    python_files = []
    
    # 遍历目录收集所有.py文件
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                python_files.append(full_path)
    
    # 按文件路径排序,保证输出顺序一致
    python_files.sort()
    
    # 打开输出文件
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write('"""合并的Python代码文件"""\n\n')
        
        # 处理每个Python文件
        for file_path in python_files:
            # 获取相对路径作为文件标识
            rel_path = os.path.relpath(file_path, directory)
            
            # 写入文件分隔注释
            outfile.write(f'\n# {"="*50}\n')
            outfile.write(f'# File: {rel_path}\n')
            outfile.write(f'# {"="*50}\n\n')
            
            # 读取并写入文件内容
            with open(file_path, 'r', encoding='utf-8') as infile:
                content = infile.read()
                
                # 移除行号前缀(如果存在)
                content = re.sub(r'^\d+\|', '', content, flags=re.MULTILINE)
                
                outfile.write(content)
                outfile.write('\n')

if __name__ == '__main__':
    # 设置源代码目录和输出文件路径
    source_dir = '../backend/sql_assistant'
    output_path = '../data/temp/function_code.py'
    
    # 执行合并
    merge_python_files(source_dir, output_path)
    print(f'已将所有Python文件合并到: {output_path}')