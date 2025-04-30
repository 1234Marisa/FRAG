import json
import os
from typing import List, Dict
import requests
import time

class RAGSearcher:
    def __init__(self, api_key: str, max_results: int = 5):
        self.api_key = api_key
        self.max_results = max_results
        # 确保输出目录存在
        os.makedirs("retrieval_outputs", exist_ok=True)
        # 获取项目根目录
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(self.PROJECT_ROOT, "retrieval/outputs")
        self.search_results = {}
        
        # 设置 SerpAPI 密钥
        if api_key is None:
            api_key = os.getenv("SERPAPI_API_KEY")
            if not api_key:
                raise ValueError("请提供 SerpAPI 密钥或设置环境变量 SERPAPI_API_KEY")
        
        self.serpapi_key = api_key
        self.base_url = "https://serpapi.com/search"
        
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
        """使用 SerpAPI 执行搜索"""
        results = []
        try:
            # 构建请求参数
            params = {
                "api_key": self.serpapi_key,
                "q": query,
                "engine": "google",  # 使用 Google 搜索引擎
                "num": self.max_results,  # 获取前 max_results 个结果
            }
            
            # 发送请求
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()  # 检查请求是否成功
            
            # 解析结果
            data = response.json()
            
            # 处理搜索结果
            if "organic_results" in data:
                for result in data["organic_results"]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", ""),
                        "position": result.get("position", 0)
                    })
            
            # 添加延迟以避免触发 API 限制
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            print(f"SerpAPI 请求出错: {e}")
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
    # 使用提供的 API 密钥
    api_key = "4909fb91e8fd3de0d2d3a7948c5d568ee63ec9bc0a4a4f3e6b22d2babfa99588"
    searcher = RAGSearcher(api_key=api_key)
    searcher.process_all_paths()

def run_retrieval():
    """独立运行检索模块的入口点"""
    print("开始运行检索模块...")
    main()
    print("检索模块运行完成！")

if __name__ == "__main__":
    run_retrieval() 