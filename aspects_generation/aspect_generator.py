from openai import OpenAI
from typing import List

class AspectGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gpt-4o"
        self.model_client = OpenAI(api_key=api_key)
        print(f"初始化 AspectGenerator，使用模型: {self.model}")

    def generate_aspects(self, parent_aspect: str, level: str = "first") -> List[str]:
        """生成子角度列表"""
        print(f"正在为 '{parent_aspect}' 生成子角度...")
        prompt = f"""
You are an expert in analyzing questions from multiple perspectives.
Given the parent aspect: "{parent_aspect}", generate EXACTLY 3 key sub-aspects that are:
1. Directly relevant to the parent aspect
2. Mutually exclusive
3. Collectively exhaustive
4. Clear and concise (preferably 2-4 words each)

Return only the list of 3 sub-aspects, one per line, without any additional text.

Example format:
Health Benefits
Cultural Impact
Taste Profile
"""
        try:
            print("正在调用 OpenAI API...")
            response = self.model_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500,
            )
            aspects = response.choices[0].message.content.strip().split('\n')
            result = [aspect.strip() for aspect in aspects if aspect.strip()]
            print(f"生成的角度: {result}")
            return result
        except Exception as e:
            print(f"生成角度时出错: {e}")
            return []

    def generate_answer(self, question: str, aspect_tree: List[str]) -> str:
        """根据问题和使用者提供的角度树生成回答"""
        prompt = f"""
You are an expert in providing comprehensive and fair answers to questions.

Question: {question}

Please analyze this question from the following aspects:
{chr(10).join([f"- {aspect}" for aspect in aspect_tree])}

Provide a detailed answer that:
1. Addresses each aspect systematically
2. Maintains fairness and objectivity
3. Considers multiple perspectives
4. Provides balanced viewpoints
"""
        try:
            response = self.model_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error during answer generation: {e}")
            return "抱歉，生成回答时出现错误。"
