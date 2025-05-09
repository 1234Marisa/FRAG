import os
import sys
from tot_refxn import AspectTreeBuilderReflexion

def main():
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python run.py <jsonl文件路径> [问题数量]")
        sys.exit(1)
    
    # 获取JSONL文件路径
    jsonl_path = sys.argv[1]
    if not os.path.exists(jsonl_path):
        print(f"错误: 文件 {jsonl_path} 不存在")
        sys.exit(1)
    
    # 获取问题数量（可选）
    num_questions = 10  # 默认值
    if len(sys.argv) > 2:
        try:
            num_questions = int(sys.argv[2])
        except ValueError:
            print("错误: 问题数量必须是整数")
            sys.exit(1)
    
    # 创建构建器实例
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: 请在环境变量中设置 OPENAI_API_KEY")
        sys.exit(1)
    
    builder = AspectTreeBuilderReflexion(api_key=api_key)
    
    # 处理JSONL文件中的问题
    builder.process_jsonl_questions(jsonl_path, num_questions)

if __name__ == "__main__":
    main() 