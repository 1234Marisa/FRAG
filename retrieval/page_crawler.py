import os
import json
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

class PageCrawler:
    def __init__(self, output_dir: str = "retrieval/outputs"):
        # 获取项目根目录
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(self.PROJECT_ROOT, output_dir)
        self.crawled_urls = set()
        self.content_results = {}
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化 Selenium
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')  # 无头模式
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')
        
    def _is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
            
    def _get_article_content(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """使用 Selenium 提取文章内容"""
        driver = None
        for attempt in range(max_retries):
            try:
                if driver:
                    driver.quit()
                
                # 使用 webdriver_manager 自动安装和管理 Chrome 驱动
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=self.chrome_options)
                driver.set_page_load_timeout(20)
                
                print(f"正在加载页面 ({attempt + 1}/{max_retries}): {url}")
                driver.get(url)
                
                # 等待页面加载
                time.sleep(5)  # 等待动态内容加载
                
                # 尝试等待主要内容加载
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                        or EC.presence_of_element_located((By.TAG_NAME, "main"))
                        or EC.presence_of_element_located((By.TAG_NAME, "p"))
                    )
                except:
                    print("等待内容加载超时，使用当前页面内容")
                
                # 获取页面内容
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # 移除不需要的元素
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()
                
                # 获取标题
                title = driver.title
                
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
                    time.sleep(2)
                    continue
                
                return {
                    'title': title,
                    'text': text[:5000] if len(text) > 5000 else text,  # 限制内容长度
                    'url': url
                }
                
            except Exception as e:
                print(f"提取文章内容时出错 ({attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        return None
            
    def crawl_url(self, url: str) -> Optional[Dict]:
        """抓取单个URL的内容"""
        if not self._is_valid_url(url):
            print(f"无效的URL: {url}")
            return None
            
        if url in self.crawled_urls:
            print(f"URL已抓取过: {url}")
            return self.content_results.get(url)
            
        print(f"正在抓取: {url}")
        content = self._get_article_content(url)
        
        if content:
            self.crawled_urls.add(url)
            self.content_results[url] = content
            return content
            
        return None
        
    def process_all_urls(self, urls: List[str] = None):
        """处理所有URL"""
        if urls is None:
            # 从检索结果中获取URL
            urls = self._load_urls_from_search_results()
            
        urls=urls[:6]
        for url in urls:
            self.crawl_url(url)
            time.sleep(1)  # 避免请求过于频繁
            
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

def main():
    # 创建爬虫实例
    crawler = PageCrawler()
    
    # 处理所有URL
    crawler.process_all_urls()
    
    # 保存结果
    crawler.save_content_results()
    
    print("网页内容抓取完成！")

if __name__ == "__main__":
    main() 