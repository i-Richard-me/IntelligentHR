import csv
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
sys.path.append(project_root)

from backend.data_processing.table_operation.table_operations import *


def get_tools_description(tools):
    """获取工具函数的描述。"""
    descriptions = []
    for tool in tools:
        descriptions.append(
            {
                "tool_name": tool.name,
                "description": tool.description,
                "args": str(tool.args),
            }
        )
    return descriptions


def generate_csv(tools, output_file):
    """生成包含工具描述的CSV文件。"""
    descriptions = get_tools_description(tools)

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["tool_name", "description", "args"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for desc in descriptions:
            writer.writerow(desc)


if __name__ == "__main__":
    tools = [
        join_dataframes,
        reshape_wide_to_long,
        reshape_long_to_wide,
        compare_dataframes,
        stack_dataframes,
    ]

    output_file = os.path.join("data", "datasets", "tools_description.csv")
    generate_csv(tools, output_file)
    print(f"CSV file '{output_file}' has been generated successfully.")
