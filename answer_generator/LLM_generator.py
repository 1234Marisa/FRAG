import os
import json
import time
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

class LLMGenerator:
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Please set it in the .env file or pass it as a parameter.")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
        # 获取项目根目录
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    def _load_content_data(self, question_id: int) -> List[Dict]:
        """加载指定问题的精炼后内容数据"""
        content_path = os.path.join(self.PROJECT_ROOT, "retrieval/outputs/refined_contents", f"refined_content_question_{question_id}.json")
        try:
            with open(content_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载问题 {question_id} 的内容数据时出错: {e}")
            return []
            
    def _create_context(self, content_data: List[Dict]) -> str:
        """创建上下文"""
        if not content_data:
            return ""
            
        # 构建上下文
        context = ""
        for item in content_data:
            context += f"来源: {item['url']}\n"
            context += f"标题: {item['title']}\n"
            context += f"内容: {item['text']}\n\n"
                
        return context
            
    def generate_answer(self, question_id: int, query: str, max_tokens: int = 1000) -> str:
        """生成答案"""
        # 加载内容数据
        content_data = self._load_content_data(question_id)
        
        # 创建上下文
        context = self._create_context(content_data)
        
        if not context:
            return "抱歉，无法找到相关信息。"
            
        # 构建提示
        prompt = f"""Based on the following reference information, please answer the user's question. Make sure that your response:

Fully considers and integrates the reference information

Is written in clear and concise language

Directly addresses the requirements of the question

Reference Information:
{context}

Question:
{query}

Please provide your answer.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional analysis assistant, skilled at deeply understanding the text content and conducting comprehensive analysis. Your response should be based on the provided context information and remain objective and professional."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"生成答案时出错: {e}")
            return "抱歉，生成答案时出现错误。"
            
    def save_answer(self, question_id: int, query: str, answer: str):
        """保存答案"""
        try:
            output_dir = os.path.join(self.PROJECT_ROOT, "answer_generator/outputs", f"question_{question_id}")
            os.makedirs(output_dir, exist_ok=True)
            
            filepath = os.path.join(output_dir, "answer.json")
            data = {
                "question": query,
                "answer": answer,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            print(f"答案已保存到: {filepath}")
            
        except Exception as e:
            print(f"保存答案时出错: {e}")

    def get_content_files_count(self) -> int:
        """获取contents目录中的文件数量"""
        contents_dir = os.path.join(self.PROJECT_ROOT, "retrieval/outputs/contents")
        try:
            files = [f for f in os.listdir(contents_dir) if f.startswith("content_results_question_")]
            return len(files)
        except Exception as e:
            print(f"获取文件数量时出错: {e}")
            return 0

    def load_questions_from_jsonl(self, jsonl_path: str, count: int) -> List[str]:
        """从JSONL文件按顺序加载指定数量的问题"""
        questions = []
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= count:
                        break
                    data = json.loads(line)
                    # 检查数据格式并打印
                    print(f"读取第 {i+1} 行数据: {data}")
                    # 获取问题字段
                    question = data.get("prompt", "")
                    if not question:
                        print(f"警告：第 {i+1} 行数据中没有找到问题字段")
                        continue
                    questions.append(question)
                    print(f"成功读取问题: {question}")
        except Exception as e:
            print(f"读取JSONL文件时出错: {e}")
        return questions

    def process_all_questions(self):
        """处理所有问题"""
        # 获取contents目录中的文件数量
        file_count = self.get_content_files_count()
        if file_count == 0:
            print("未找到任何内容文件")
            return
            
        print(f"找到 {file_count} 个内容文件")
        
        # 从JSONL文件加载对应数量的问题
        jsonl_path = os.path.join(self.PROJECT_ROOT, "data/ultrachat_200k/short_prompt_ultrachat_200k_train_gen.jsonl")
        print(f"正在从文件读取问题: {jsonl_path}")
        questions = self.load_questions_from_jsonl(jsonl_path, file_count)
        
        if not questions:
            print("未能从JSONL文件加载到任何问题")
            return
            
        print(f"从JSONL文件加载了 {len(questions)} 个问题")
        
        # 处理每个问题
        for i, question in enumerate(questions, 1):
            print(f"\n处理问题 {i}...")
            print(f"当前问题: {question}")
            
            # 生成答案
            answer = self.generate_answer(i, question)
            
            # 保存答案
            self.save_answer(i, question, answer)

def main():
    # 使用环境变量获取 API 密钥
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 创建生成器实例
    generator = LLMGenerator(api_key=api_key)
    
    # 处理所有问题
    generator.process_all_questions()

if __name__ == "__main__":
    main() 