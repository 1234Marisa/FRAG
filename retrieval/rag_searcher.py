import json
import os
from typing import List, Dict
import requests
import time
from dotenv import load_dotenv
from openai import OpenAI

class RAGSearcher:
    def __init__(self, api_key: str = None, max_results: int = 5):
        load_dotenv()
        self.api_key = api_key or os.getenv("BING_SEARCH_V7_SUBSCRIPTION_KEY")
        if not self.api_key:
            raise ValueError("Bing Search API key is required. Please set it in the .env file or pass it as a parameter.")
        
        self.endpoint = os.getenv("BING_SEARCH_V7_ENDPOINT", "https://api.bing.microsoft.com")
        self.max_results = max_results
        # 获取项目根目录
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(self.PROJECT_ROOT, "retrieval/outputs/urls")
        self.search_results = {}
        
        # 初始化OpenAI客户端
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def load_tree_paths(self, question_id: int) -> List[List[str]]:
        """从指定问题的paths.json加载所有路径"""
        filepath = os.path.join(self.PROJECT_ROOT, f"aspects_generation/aspects_outputs/question_{question_id}/paths.json")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def polish_search_query(self, path: List[str]) -> str:
        """使用LLM润色搜索语句"""
        prompt = f"""
Please convert the following path into an effective search query. Each part of the path represents a different aspect of the question.
Path: {' -> '.join(path)}

Requirements:
1. Maintain the original semantics
2. Use natural language
3. Add necessary connecting words
4. Ensure the query is fluent
5. Do not add extra information

Return only the polished search query, without any additional content.
"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error while polishing search query: {e}")
            return " ".join(path)  # 如果出错，返回原始路径
    
    def search_path(self, path: List[str]) -> List[Dict]:
        """搜索单个路径的相关内容"""
        # 润色搜索语句
        polished_query = self.polish_search_query(path)
        print(f"\n原始路径: {' -> '.join(path)}")
        print(f"润色后的搜索语句: {polished_query}")
        
        results = self._perform_search(polished_query)
        return results
    
    def _perform_search(self, query: str) -> List[Dict]:
        """使用 Bing Search API 执行搜索"""
        results = []
        try:
            # 构建请求头
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key
            }
            
            # 构建请求参数
            params = {
                "q": query,
                "count": self.max_results,
                "responseFilter": "Webpages",
                "textFormat": "Raw"
            }
            
            # 发送请求
            response = requests.get(
                f"{self.endpoint}/v7.0/search",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            # 解析结果
            data = response.json()
            
            # 处理搜索结果
            if "webPages" in data and "value" in data["webPages"]:
                for result in data["webPages"]["value"]:
                    results.append({
                        "title": result.get("name", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", ""),
                        "position": result.get("position", 0)
                    })
            
            # 添加延迟以避免触发 API 限制
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            print(f"Bing Search API 请求出错: {e}")
        except Exception as e:
            print(f"处理搜索结果时出错: {e}")
        
        return results
    
    def save_search_results(self, question_id: int):
        """保存搜索结果到文件"""
        filepath = os.path.join(self.output_dir, f"search_results_question_{question_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.search_results, f, ensure_ascii=False, indent=2)
        print(f"搜索结果已保存到 {filepath}")
    
    def process_all_paths(self, question_id: int):
        """处理指定问题的所有路径的搜索"""
        paths = self.load_tree_paths(question_id)
        
        for path in paths:
            path_str = " -> ".join(path)
            self.search_results[path_str] = self.search_path(path)
        
        self.save_search_results(question_id)

    def get_all_question_ids(self) -> List[int]:
        """获取所有问题文件夹的ID"""
        aspects_outputs_dir = os.path.join(self.PROJECT_ROOT, "aspects_generation/aspects_outputs")
        question_dirs = [d for d in os.listdir(aspects_outputs_dir) if d.startswith("question_")]
        return [int(d.split("_")[1]) for d in question_dirs]

    def process_all_questions(self):
        """处理所有问题的路径搜索"""
        question_ids = self.get_all_question_ids()
        print(f"Found {len(question_ids)} questions to process")
        
        for question_id in question_ids:
            print(f"\nProcessing question {question_id}...")
            self.search_results = {}  # 清空之前的结果
            self.process_all_paths(question_id)

def main():
    # 使用环境变量获取 API 密钥
    load_dotenv()
    api_key = os.getenv("BING_SEARCH_V7_SUBSCRIPTION_KEY")
    searcher = RAGSearcher(api_key=api_key)
    
    # 处理所有问题
    searcher.process_all_questions()

def run_retrieval():
    """独立运行检索模块的入口点"""
    print("开始运行检索模块...")
    main()
    print("检索模块运行完成！")

if __name__ == "__main__":
    run_retrieval() 