import json
from typing import List, Dict, Any
from openai import OpenAI
from collections import defaultdict
import numpy as np

class ContentSelector:
    def __init__(self, refined_content_path: str = "retrieval/outputs/refined_content.json"):
        """初始化内容选择器"""
        self.refined_content_path = refined_content_path
        self.content_tags = {
            'country': [],  # 国家
            'region': [],   # 地区
            'source_type': []  # 来源类型
        }
        self.client = OpenAI()
        
    def _load_refined_content(self) -> List[Dict[str, Any]]:
        """加载精炼后的内容"""
        try:
            with open(self.refined_content_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载内容时出错: {e}")
            return []
            
    def _analyze_content_tags(self, content: Dict[str, Any], query: str) -> Dict[str, str]:
        """使用LLM分析内容的标签"""
        prompt = f"""请分析以下内容，并为其添加标签。标签包括：
1. 国家（如：中国、美国、日本等）
2. 地区（如：北方、南方、东部、西部等）
3. 来源类型（如：大媒体、小媒体、大V、个人博主等）

内容：
标题：{content['title']}
文本：{content['text']}

请以JSON格式返回标签，格式如下：
{{
    "country": "国家",
    "region": "地区",
    "source_type": "来源类型"
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一个专业的内容分析助手，擅长为内容添加准确的标签。"},
                    {"role": "user", "content": prompt}
                ]
            )
            tags = json.loads(response.choices[0].message.content)
            return tags
        except Exception as e:
            print(f"分析标签时出错: {e}")
            return {"country": "未知", "region": "未知", "source_type": "未知"}
            
    def _calculate_fairness_score(self, content_tags: List[Dict[str, str]]) -> List[float]:
        """计算每个内容的公平性分数"""
        # 统计各标签的分布
        tag_distributions = {
            'country': defaultdict(int),
            'region': defaultdict(int),
            'source_type': defaultdict(int)
        }
        
        # 计算每个标签的出现次数
        for tags in content_tags:
            for tag_type, tag_value in tags.items():
                tag_distributions[tag_type][tag_value] += 1
                
        # 计算每个内容的公平性分数
        fairness_scores = []
        total_contents = len(content_tags)
        
        for tags in content_tags:
            score = 0.0
            for tag_type, tag_value in tags.items():
                # 计算该标签值的占比
                tag_count = tag_distributions[tag_type][tag_value]
                tag_ratio = tag_count / total_contents
                # 将占比转换为分数（占比越小，分数越高）
                score += (1 - tag_ratio)
            fairness_scores.append(score)
            
        return fairness_scores
        
    def select_contents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """选择内容，考虑公平性"""
        contents = self._load_refined_content()
        if not contents:
            return []
            
        # 为每个内容添加标签
        content_tags = []
        for content in contents:
            tags = self._analyze_content_tags(content, query)
            content_tags.append(tags)
            
        # 计算公平性分数
        fairness_scores = self._calculate_fairness_score(content_tags)
        
        # 将内容和分数组合
        content_with_scores = list(zip(contents, fairness_scores))
        
        # 按分数排序并选择top_k个内容
        selected_contents = sorted(content_with_scores, key=lambda x: x[1], reverse=True)[:top_k]
        
        # 返回选中的内容（不包含分数）
        return [content for content, _ in selected_contents]
        
    def save_selected_contents(self, query: str, output_path: str = "retrieval/outputs/selected_contents.json"):
        """保存选中的内容"""
        selected_contents = self.select_contents(query)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(selected_contents, f, ensure_ascii=False, indent=2)
            print(f"选中的内容已保存到: {output_path}")
        except Exception as e:
            print(f"保存内容时出错: {e}")
            
def main():
    selector = ContentSelector()
    query = "tell me some good food"  # 示例查询
    selector.save_selected_contents(query)
    
if __name__ == "__main__":
    main()
