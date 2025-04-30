from aspects_generation.aspect_tree_builder import AspectTreeBuilderDynamic
from retrieval.rag_searcher import RAGSearcher
from retrieval.page_crawler import PageCrawler
from answer_generator.LLM_generator import LLMGenerator
import os
import json
from dotenv import load_dotenv
def load_question(question_id: int = None) -> str:
    """从 questions.json 加载问题"""
    questions_path = os.path.join("data", "questions.json")
    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
    except Exception as e:
        print(f"读取问题文件时出错: {e}")
        return None
    
    # 如果没有指定问题ID，让用户选择
    if question_id is None:
        print("\n可用的问题：")
        for q in questions_data["questions"]:
            print(f"{q['id']}. {q['question']}")
        try:
            question_id = int(input("\n请选择问题ID："))
        except ValueError:
            print("请输入有效的数字ID")
            return None
    
    # 获取选中的问题
    for q in questions_data["questions"]:
        if q["id"] == question_id:
            return q["question"]
    
    print(f"未找到ID为 {question_id} 的问题")
    return None

def run_pipeline(question: str):
    """运行完整的处理流程"""
    load_dotenv()
    
    # 获取 API 密钥
    openai_api_key = os.getenv("OPENAI_API_KEY")
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    
    if not openai_api_key:
        raise ValueError("OpenAI API key is required. Please set it in the .env file.")
    if not serpapi_key:
        raise ValueError("SERPAPI API key is required. Please set it in the .env file.")
    
    # 1. 构建角度树
    print("\n第一步：生成角度树...")
    tree_builder = AspectTreeBuilderDynamic(openai_api_key)
    aspect_tree = tree_builder.build_tree(question)
    
    # 打印角度树
    print("\n生成的角度树结构：")
    tree_builder.print_tree(aspect_tree)
    
    # 保存树形结构和路径
    tree_builder.save_tree_structure(aspect_tree)
    tree_builder.save_tree_paths(aspect_tree)
    
    # 2. 进行检索
    print("\n第二步：进行检索...")
    searcher = RAGSearcher(api_key=serpapi_key)
    searcher.process_all_paths()
    
    # 3. 抓取网页内容
    print("\n第三步：抓取网页内容...")
    crawler = PageCrawler()
    crawler.process_all_urls()
    crawler.save_content_results()
    
    # 4. 生成答案
    print("\n第四步：生成答案...")
    generator = LLMGenerator(api_key=openai_api_key)
    answer = generator.generate_answer(question)
    
    # 打印答案
    print("\n生成的答案：")
    print(answer)
    
    # 保存答案
    generator.save_answer(question, answer)
    
    print("\n处理完成！")
    print("角度树已保存到 aspects_outputs/ 目录")
    print("检索结果和网页内容已保存到 retrieval/outputs/ 目录")
    print("答案已保存到 answer_generator/outputs/ 目录")

def main():
    """主函数"""
    print("欢迎使用 FRAG 系统！")
    
    # 加载问题
    question = load_question()
    if not question:
        return
    
    # 运行处理流程
    run_pipeline(question)

if __name__ == "__main__":
    main()
