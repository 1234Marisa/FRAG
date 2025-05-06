import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

class AnswerScorer:
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        """初始化答案评分器"""
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Please set it in the .env file or pass it as a parameter.")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
        # 获取项目根目录
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.answer_path = os.path.join(self.PROJECT_ROOT, "answer_generator/outputs/answer.json")
        
    def evaluate_answer(self, query: str, answer: str) -> Dict[str, Any]:
        """评估答案质量"""
        prompt = f"""Please evaluate the following question and answer in detail. Rate each aspect on a scale of 1-10 and provide specific explanations.

Question: {query}

Answer: {answer}

Please evaluate the following aspects:

1. Relevance:
- Does the answer directly address the core content of the question
- Is it free from irrelevant information
- Does it meet the actual needs of the questioner

2. Accuracy:
- Is the information accurate and error-free
- Is it supported by reliable sources
- Are there any factual errors

3. Perspective Diversity:
- Does it analyze the question from multiple angles
- Does it consider different viewpoints and approaches
- Is there a logical connection between different perspectives

4. Source Diversity:
- Are the information sources diverse
- Does it include different types of reference materials
- Are the sources representative and authoritative

5. Fairness:
- Is the content balanced across different aspects
- Is it free from bias and subjective judgment
- Does it give appropriate attention to each aspect

Please provide the evaluation results in the following JSON format:
{{
    "scores": {{
        "relevance": {{
            "score": 8,
            "explanation": "The answer directly addresses the core question and provides specific examples"
        }},
        "accuracy": {{
            "score": 9,
            "explanation": "Information is accurate and supported by reliable sources"
        }},
        "perspective_diversity": {{
            "score": 7,
            "explanation": "Analyzes from multiple angles, but some perspectives could be more in-depth"
        }},
        "source_diversity": {{
            "score": 8,
            "explanation": "Cites various reliable sources with rich source types"
        }},
        "fairness": {{
            "score": 8,
            "explanation": "Content is balanced across aspects and free from obvious bias"
        }}
    }},
    "overall_score": 8,
    "summary": "The answer performs well overall, with accurate information and multi-angle analysis"
}}

Note: Please ensure the response is in valid JSON format.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional answer quality assessment expert. Please provide detailed, objective evaluations and always respond in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            # 获取响应内容
            content = response.choices[0].message.content.strip()
            
            # 尝试解析JSON
            try:
                evaluation = json.loads(content)
                
                # 验证JSON结构
                required_keys = ["scores", "overall_score", "summary"]
                score_keys = ["relevance", "accuracy", "perspective_diversity", "source_diversity", "fairness"]
                
                if not all(key in evaluation for key in required_keys):
                    raise ValueError("缺少必需的评估键")
                    
                if not all(key in evaluation["scores"] for key in score_keys):
                    raise ValueError("缺少必需的评分键")
                    
                for score in evaluation["scores"].values():
                    if not isinstance(score.get("score"), (int, float)) or not isinstance(score.get("explanation"), str):
                        raise ValueError("评分格式无效")
                
                # 计算总分（加权平均）
                weights = {
                    "relevance": 0.25,      # 相关性权重最高
                    "accuracy": 0.25,       # 正确性权重同样重要
                    "perspective_diversity": 0.2,
                    "source_diversity": 0.15,
                    "fairness": 0.15
                }
                
                weighted_score = sum(
                    score["score"] * weights[key]
                    for key, score in evaluation["scores"].items()
                )
                
                evaluation["overall_score"] = round(weighted_score, 2)
                
                return evaluation
                
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"原始响应: {content}")
                return None
                
        except Exception as e:
            print(f"评估答案时出错: {e}")
            return None
            
    def score_answer(self):
        """对答案进行评分并更新文件"""
        try:
            # 读取答案文件
            with open(self.answer_path, 'r', encoding='utf-8') as f:
                answer_data = json.load(f)
            
            # 评估答案
            evaluation = self.evaluate_answer(answer_data['query'], answer_data['answer'])
            
            if evaluation:
                # 添加评分结果
                answer_data['evaluation'] = evaluation
                
                # 保存更新后的文件
                with open(self.answer_path, 'w', encoding='utf-8') as f:
                    json.dump(answer_data, f, ensure_ascii=False, indent=2)
                
                print(f"答案评分完成，结果已保存到: {self.answer_path}")
                print(f"总体评分: {evaluation['overall_score']}")
                print(f"评分总结: {evaluation['summary']}")
            else:
                print("评分失败，无法更新文件")
                
        except FileNotFoundError:
            print(f"找不到答案文件: {self.answer_path}")
        except json.JSONDecodeError:
            print(f"答案文件格式错误: {self.answer_path}")
        except Exception as e:
            print(f"处理答案文件时出错: {e}")

def main():
    # 使用环境变量获取 API 密钥
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 创建评分器实例
    scorer = AnswerScorer(api_key=api_key)
    
    # 执行评分
    scorer.score_answer()

if __name__ == "__main__":
    main()
