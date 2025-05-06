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
        self.content_path = os.path.join(self.PROJECT_ROOT, "retrieval/outputs/refined_content.json")
        
        # 加载内容
        self.content_data = self._load_content_data()
        
    def _load_content_data(self) -> List[Dict]:
        """加载精炼后的内容数据"""
        try:
            with open(self.content_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告：找不到内容文件 {self.content_path}")
            return []
        except json.JSONDecodeError:
            print(f"警告：内容文件 {self.content_path} 格式错误")
            return []
        except Exception as e:
            print(f"警告：加载内容数据时出错: {e}")
            return []
            
    def _create_context(self, query: str) -> str:
        """创建上下文"""
        if not self.content_data:
            return ""
            
        # 构建上下文
        context = ""
        for item in self.content_data:
            context += f"来源: {item['url']}\n"
            context += f"标题: {item['title']}\n"
            context += f"内容: {item['text']}\n\n"
                
        return context
            
    def generate_answer(self, query: str, max_tokens: int = 1000) -> str:
        """生成答案"""
        # 创建上下文
        context = self._create_context(query)
        
        if not context:
            return "抱歉，无法找到相关信息。"
            
        # 构建提示
        prompt = f"""Carefully read and analyze the following contextual information, then answer the user's question. Please follow these guidelines when responding:

1. Thoroughly understand the context:

- Carefully review the content from each source

- Pay close attention to key details and important facts

- Understand the relationships and differences between sources

2. Synthesize and analyze:

- Integrate information from different sources

- Identify similarities and differences

3. Assess the reliability and relevance of the information

4. Answering requirements:

- Provide a comprehensive and accurate response based on the context

- Clearly cite the sources of information

- If information is insufficient, explicitly state the reason

- Maintain objectivity and professionalism

Context:
{context}

Question:
{query}

Please provide a thoughtful and detailed answer.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的分析助手，擅长深入理解文本内容并进行综合分析。你的回答应该基于提供的上下文信息，保持客观和专业。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"生成答案时出错: {e}")
            return "抱歉，生成答案时出现错误。"
            
    def save_answer(self, query: str, answer: str, filename: str = "answer.json"):
        """保存答案"""
        try:
            output_dir = os.path.join(self.PROJECT_ROOT, "answer_generator/outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            filepath = os.path.join(output_dir, filename)
            data = {
                "query": query,
                "answer": answer,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            print(f"答案已保存到: {filepath}")
            
        except Exception as e:
            print(f"保存答案时出错: {e}")

def main():
    # 使用环境变量获取 API 密钥
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 创建生成器实例
    generator = LLMGenerator(api_key=api_key)
    
    # 读取问题
    questions_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "questions.json")
    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
    except Exception as e:
        print(f"读取问题文件时出错: {e}")
        return
    
    # 显示可用问题
    print("\n可用的问题：")
    for q in questions_data["questions"]:
        print(f"{q['id']}. {q['question']}")
    
    # 让用户选择问题
    try:
        question_id = int(input("\n请选择问题ID："))
    except ValueError:
        print("请输入有效的数字ID")
        return
    
    # 获取选中的问题
    selected_question = None
    for q in questions_data["questions"]:
        if q["id"] == question_id:
            selected_question = q["question"]
            break
    
    if not selected_question:
        print(f"未找到ID为 {question_id} 的问题")
        return
    
    # 生成答案
    answer = generator.generate_answer(selected_question)
    
    # 打印答案
    print("\n答案：")
    print(answer)
    
    # 保存答案
    generator.save_answer(selected_question, answer)

if __name__ == "__main__":
    main() 