import json
import os
from typing import List, Dict
import requests
import time
from dotenv import load_dotenv

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
        self.output_dir = os.path.join(self.PROJECT_ROOT, "retrieval/outputs")
        self.search_results = {}
        
    def load_tree_paths(self) -> List[List[str]]:
        """从 tree_paths.json 加载所有路径"""
        filepath = os.path.join(self.PROJECT_ROOT, "aspects_outputs/tree_paths.json")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def search_path(self, path: List[str]) -> List[Dict]:
        """搜索单个路径的相关内容"""
        # 将路径转换为搜索查询
        query = " ".join(path)
        print(f"\n正在搜索路径: {' -> '.join(path)}")
        
        results = self._perform_search(query)
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
            response.raise_for_status()  # 检查请求是否成功
            
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
    
    def save_search_results(self):
        """保存搜索结果到文件"""
        filepath = os.path.join(self.output_dir, "search_results.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.search_results, f, ensure_ascii=False, indent=2)
        print(f"搜索结果已保存到 {filepath}")
    
    def process_all_paths(self):
        """处理所有路径的搜索"""
        paths = self.load_tree_paths()
        
        for path in paths:
            path_str = " -> ".join(path)
            self.search_results[path_str] = self.search_path(path)
        
        self.save_search_results()

def main():
    # 使用环境变量获取 API 密钥
    load_dotenv()
    api_key = os.getenv("BING_SEARCH_V7_SUBSCRIPTION_KEY")
    searcher = RAGSearcher(api_key=api_key)
    searcher.process_all_paths()

def run_retrieval():
    """独立运行检索模块的入口点"""
    print("开始运行检索模块...")
    main()
    print("检索模块运行完成！")

if __name__ == "__main__":
    run_retrieval() 