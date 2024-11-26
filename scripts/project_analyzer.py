import os
import sys
from radon.raw import analyze
from radon.metrics import h_visit
from radon.complexity import cc_visit


def analyze_project(directory):
    total_loc = 0
    total_sloc = 0
    total_comments = 0
    total_multi = 0
    total_blank = 0
    total_files = 0
    max_complexity = 0
    total_complexity = 0
    complexity_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 原始指标分析
                analysis = analyze(content)
                total_loc += analysis.loc
                total_sloc += analysis.sloc
                total_comments += analysis.comments
                total_multi += analysis.multi
                total_blank += analysis.blank
                total_files += 1

                # 圈复杂度分析
                complexity = cc_visit(content)
                if complexity:
                    file_max_complexity = max(item.complexity for item in complexity)
                    max_complexity = max(max_complexity, file_max_complexity)
                    total_complexity += sum(item.complexity for item in complexity)

                    for item in complexity:
                        if item.complexity <= 5:
                            complexity_counts["A"] += 1
                        elif item.complexity <= 10:
                            complexity_counts["B"] += 1
                        elif item.complexity <= 20:
                            complexity_counts["C"] += 1
                        elif item.complexity <= 30:
                            complexity_counts["D"] += 1
                        elif item.complexity <= 40:
                            complexity_counts["E"] += 1
                        else:
                            complexity_counts["F"] += 1

                # Halstead 指标
                h_visit_result = h_visit(content)
                if h_visit_result:
                    # 这里可以添加 Halstead 指标的处理，如果需要的话
                    pass

    return {
        "total_files": total_files,
        "total_loc": total_loc,
        "total_sloc": total_sloc,
        "total_comments": total_comments,
        "total_multi": total_multi,
        "total_blank": total_blank,
        "max_complexity": max_complexity,
        "avg_complexity": total_complexity / total_files if total_files > 0 else 0,
        "complexity_counts": complexity_counts,
    }


def main():
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print("正在分析项目...")
    results = analyze_project(project_root)

    print("\n项目分析结果:")
    print(f"总文件数: {results['total_files']}")
    print(f"总行数 (LOC): {results['total_loc']}")
    print(f"代码行数 (SLOC): {results['total_sloc']}")
    print(f"注释行数: {results['total_comments']}")
    print(f"多行注释行数: {results['total_multi']}")
    print(f"空白行数: {results['total_blank']}")
    print(f"\n最大圈复杂度: {results['max_complexity']}")
    print(f"平均圈复杂度: {results['avg_complexity']:.2f}")

    print("\n圈复杂度分布:")
    for grade, count in results["complexity_counts"].items():
        print(f"  等级 {grade}: {count}")


if __name__ == "__main__":
    main()
