import os
import json
import time
import asyncio
import aiohttp
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import datetime
import random

class PageCrawler:
    def __init__(self, output_dir: str = "retrieval/outputs", max_concurrent: int = 5):
        # 获取项目根目录
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(self.PROJECT_ROOT, output_dir)
        self.crawled_urls: Set[str] = set()
        self.content_results: Dict = {}
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化 UserAgent
        self.ua = UserAgent()
        
        # 代理列表（示例，需要替换为实际可用的代理）
        self.proxies = [
            None,  # 直连
            # 添加您的代理服务器
            # "http://proxy1.example.com:8080",
            # "http://proxy2.example.com:8080",
        ]
        
    def _is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
            
    def _get_headers(self) -> Dict:
        """生成随机请求头"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers',
            'DNT': '1',
        }
        
    async def _get_article_content(self, url: str, session: aiohttp.ClientSession, max_retries: int = 3) -> Optional[Dict]:
        """使用 aiohttp 异步提取文章内容"""
        headers = self._get_headers()
        proxy = random.choice(self.proxies)
        
        for attempt in range(max_retries):
            try:
                print(f"正在加载页面 ({attempt + 1}/{max_retries}): {url}")
                async with self.semaphore:  # 限制并发数
                    async with session.get(url, headers=headers, proxy=proxy, timeout=10) as response:
                        response.raise_for_status()
                        html = await response.text()
                
                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # 移除不需要的元素
                for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "form"]):
                    element.decompose()
                
                # 获取标题
                title = soup.title.string if soup.title else url
                
                # 获取正文内容
                article = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile('content|article|post|entry'))
                
                if article:
                    text = article.get_text(separator=' ', strip=True)
                else:
                    # 如果没有找到特定标签，获取所有段落
                    paragraphs = soup.find_all('p')
                    text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                
                # 清理文本
                text = re.sub(r'\s+', ' ', text).strip()
                
                # 检查是否成功提取到内容
                if not text or len(text) < 50:
                    print(f"提取的内容过少，尝试重试 ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(1)
                    continue
                
                return {
                    'title': title,
                    'text': text[:10000] if len(text) > 10000 else text,  # 限制内容长度
                    'url': url,
                    'crawl_time': datetime.now().isoformat()
                }
                
            except Exception as e:
                print(f"提取文章内容时出错 ({attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
        
        return None
            
    async def crawl_url(self, url: str, session: aiohttp.ClientSession) -> Optional[Dict]:
        """异步抓取单个URL的内容"""
        if not self._is_valid_url(url):
            print(f"无效的URL: {url}")
            return None
            
        if url in self.crawled_urls:
            print(f"URL已抓取过: {url}")
            return self.content_results.get(url)
            
        print(f"正在抓取: {url}")
        content = await self._get_article_content(url, session)
        
        if content:
            self.crawled_urls.add(url)
            self.content_results[url] = content
            return content
            
        return None
        
    async def process_urls(self, urls: List[str]):
        """异步处理所有URL"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.crawl_url(url, session) for url in urls]
            await asyncio.gather(*tasks)
            
    async def process_all_urls(self, urls: List[str] = None):
        """处理所有URL的主函数"""
        if urls is None:
            # 从检索结果中获取URL
            urls = self._load_urls_from_search_results()
            
        # 运行异步任务
        await self.process_urls(urls)
            
    def _load_urls_from_search_results(self) -> List[str]:
        """从检索结果中加载URL"""
        try:
            search_results_path = os.path.join(self.output_dir, "search_results.json")
            print(f"正在从 {search_results_path} 加载检索结果...")
            
            with open(search_results_path, 'r', encoding='utf-8') as f:
                search_results = json.load(f)
                
            urls = set()
            for path_results in search_results.values():
                for result in path_results:
                    if 'url' in result:
                        urls.add(result['url'])
                        
            print(f"成功加载 {len(urls)} 个URL")
            return list(urls)
        except Exception as e:
            print(f"加载检索结果时出错: {e}")
            return []
            
    def save_content_results(self, filename: str = "content_results.json"):
        """保存抓取的内容结果"""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.content_results, f, ensure_ascii=False, indent=2)
        print(f"内容结果已保存到: {filepath}")
        
    def load_content_results(self, filename: str = "content_results.json") -> Dict:
        """加载已保存的内容结果"""
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载内容结果时出错: {e}")
            return {}

async def main():
    # 创建爬虫实例
    crawler = PageCrawler()
    
    # 处理所有URL
    await crawler.process_all_urls()
    
    # 保存结果
    crawler.save_content_results()
    
    print("网页内容抓取完成！")

if __name__ == "__main__":
    asyncio.run(main()) 