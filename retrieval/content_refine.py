import json
import os
from typing import List, Dict, Any
from openai import OpenAI
import re
from tqdm import tqdm

class ContentRefiner:
    def __init__(self, api_key: str):
        """初始化内容精炼器"""
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.max_tokens = 2000  # 每个内容的最大token数
        self.min_content_length = 100  # 最小内容长度
        # 获取项目根目录
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(self.PROJECT_ROOT, "retrieval/outputs")
        
    def clean_text(self, text: str) -> str:
        """清理文本，去除无意义内容"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        
        # 移除重复的标点符号
        text = re.sub(r'([.,!?])\1+', r'\1', text)
        
        return text.strip()
    
    def summarize_content(self, title: str, content: str) -> str:
        """使用LLM对内容进行总结"""
        prompt = f"""
Please produce a concise summary of the following article, retaining key information and removing redundant content.

Title: {title}

Original Text:
{content}

Requirements:

1. Preserve the core ideas and essential information

2. Eliminate repeated or unnecessary content

3. Use clear and concise language

4. Ensure logical coherence throughout

Please output only the summarized content without any additional explanation.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"总结内容时出错: {e}")
            return content
    
    def process_content(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个内容项"""
        # 清理标题
        title = self.clean_text(content_item.get('title', ''))
        
        # 清理正文
        text = self.clean_text(content_item.get('text', ''))
        
        # 如果内容太短，可能是无意义内容
        if len(text) < self.min_content_length:
            return None
        
        # 总结内容
        summarized_text = self.summarize_content(title, text)
        
        return {
            'title': title,
            'text': summarized_text,
            'url': content_item.get('url', ''),
            'crawl_time': content_item.get('crawl_time', '')
        }
    
    def refine_contents(self, question_id: int):
        """处理指定问题的所有内容"""
        print(f"开始处理问题 {question_id} 的内容")
        
        # 构建输入输出文件路径
        input_file = os.path.join(self.output_dir, "contents", f"content_results_question_{question_id}.json")
        output_file = os.path.join(self.output_dir, "refined_contents", f"refined_content_question_{question_id}.json")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 读取原始内容
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                contents = json.load(f)
        except Exception as e:
            print(f"读取文件 {input_file} 时出错: {e}")
            return
        
        # 处理每个内容项
        refined_contents = []
        for url, item in tqdm(contents.items(), desc=f"处理问题 {question_id} 的内容"):
            # 确保item是字典类型
            if isinstance(item, dict):
                item['url'] = url  # 补充url字段
                refined_item = self.process_content(item)
                if refined_item:
                    refined_contents.append(refined_item)
            else:
                print(f"警告: 跳过非字典格式的内容项: {url}")
        
        # 保存处理后的内容
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(refined_contents, f, ensure_ascii=False, indent=2)
        
        print(f"问题 {question_id} 处理完成，结果保存到: {output_file}")
        print(f"原始内容数量: {len(contents)}")
        print(f"处理后内容数量: {len(refined_contents)}")

    def get_all_question_ids(self) -> List[int]:
        """获取所有问题文件夹的ID"""
        aspects_outputs_dir = os.path.join(self.PROJECT_ROOT, "aspects_generation/aspects_outputs")
        question_dirs = [d for d in os.listdir(aspects_outputs_dir) if d.startswith("question_")]
        return [int(d.split("_")[1]) for d in question_dirs]

    def process_all_questions(self):
        """处理所有问题的内容"""
        question_ids = self.get_all_question_ids()
        print(f"找到 {len(question_ids)} 个问题需要处理")
        
        for question_id in question_ids:
            print(f"\n处理问题 {question_id}...")
            self.refine_contents(question_id)

def main():
    # 使用环境变量中的API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请在环境变量中设置 OPENAI_API_KEY")
    
    # 创建内容精炼器实例
    refiner = ContentRefiner(api_key)
    
    # 处理所有问题
    refiner.process_all_questions()

if __name__ == "__main__":
    main()
