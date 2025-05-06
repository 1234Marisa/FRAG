import json
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
import tldextract
from collections import defaultdict

class URLSelector:
    def __init__(self, search_results_path: str = "retrieval/outputs/search_results.json"):
        """初始化URL选择器"""
        self.search_results_path = search_results_path
        self.domain_categories = {
            'official': ['gov', 'edu', 'org'],
            'news': ['news', 'media', 'press'],
            'blog': ['blog', 'medium', 'wordpress'],
            'forum': ['forum', 'community', 'discussion'],
            'social': ['facebook', 'twitter', 'instagram'],
            'ecommerce': ['shop', 'store', 'market'],
            'other': []
        }
        
    def _load_search_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载搜索结果"""
        try:
            with open(self.search_results_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载搜索结果时出错: {e}")
            return {}
            
    def _categorize_domain(self, url: str) -> str:
        """对域名进行分类"""
        extracted = tldextract.extract(url)
        domain = extracted.domain.lower()
        suffix = extracted.suffix.lower()
        
        # 检查是否为官方域名
        if suffix in self.domain_categories['official']:
            return 'official'
            
        # 检查其他类别
        for category, keywords in self.domain_categories.items():
            if any(keyword in domain for keyword in keywords):
                return category
                
        return 'other'
        
    def _calculate_diversity_score(self, urls: List[Dict[str, Any]]) -> float:
        """计算URL列表的多样性分数"""
        if not urls:
            return 0.0
            
        # 统计各类型的URL数量
        category_counts = defaultdict(int)
        for url in urls:
            category = self._categorize_domain(url['url'])
            category_counts[category] += 1
            
        # 计算多样性分数（使用香农熵）
        total = len(urls)
        entropy = 0.0
        for count in category_counts.values():
            p = count / total
            entropy -= p * (p * 100)  # 放大差异
            
        return entropy
        
    def _calculate_authority_score(self, url: str) -> float:
        """计算单个URL的权威性分数"""
        extracted = tldextract.extract(url)
        domain = extracted.domain.lower()
        suffix = extracted.suffix.lower()
        
        # 基础分数
        base_score = 0.0
        
        # 域名后缀权重
        suffix_weights = {
            'gov': 1.0,
            'edu': 0.9,
            'org': 0.8,
            'com': 0.7,
            'net': 0.6
        }
        base_score += suffix_weights.get(suffix, 0.5)
        
        # 域名特征权重
        if any(keyword in domain for keyword in ['news', 'media', 'press']):
            base_score += 0.2
        if any(keyword in domain for keyword in ['official', 'government']):
            base_score += 0.3
            
        return min(base_score, 1.0)
        
    def select_urls(self, min_diversity: float = 0.5, max_authority: float = 0.8) -> Dict[str, List[Dict[str, Any]]]:
        """选择URL，平衡权威性和多样性"""
        search_results = self._load_search_results()
        selected_results = {}
        
        for query, urls in search_results.items():
            # 计算当前URL列表的多样性分数
            diversity_score = self._calculate_diversity_score(urls)
            
            # 如果多样性分数太低，添加更多不同类型的URL
            if diversity_score < min_diversity:
                # 按域名类型分组
                categorized_urls = defaultdict(list)
                for url in urls:
                    category = self._categorize_domain(url['url'])
                    categorized_urls[category].append(url)
                    
                # 确保每个类别都有足够的URL
                selected_urls = []
                for category, category_urls in categorized_urls.items():
                    # 限制每个类别的URL数量，避免过度集中
                    max_urls_per_category = max(2, len(urls) // len(categorized_urls))
                    selected_urls.extend(category_urls[:max_urls_per_category])
                    
                # 按权威性分数排序
                selected_urls.sort(key=lambda x: self._calculate_authority_score(x['url']), reverse=True)
                
                # 过滤掉权威性过高的URL
                selected_urls = [
                    url for url in selected_urls 
                    if self._calculate_authority_score(url['url']) <= max_authority
                ]
                
                selected_results[query] = selected_urls
            else:
                selected_results[query] = urls
                
        return selected_results
        
    def save_selected_urls(self, output_path: str = "retrieval/outputs/selected_urls.json"):
        """保存选中的URL"""
        selected_urls = self.select_urls()
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(selected_urls, f, ensure_ascii=False, indent=2)
            print(f"选中的URL已保存到: {output_path}")
        except Exception as e:
            print(f"保存URL时出错: {e}")
            
def main():
    selector = URLSelector()
    selector.save_selected_urls()
    
if __name__ == "__main__":
    main()
