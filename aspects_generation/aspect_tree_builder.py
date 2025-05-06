# generation/aspect_tree_builder.py

from aspects_generation.aspect_node import AspectNode
from aspects_generation.aspect_generator import AspectGenerator
import os
import json

class AspectTreeBuilderDynamic:
    def __init__(self, api_key: str, max_depth: int = 3):
        self.aspect_gen = AspectGenerator(api_key)
        self.max_depth = max_depth  # 添加最大深度限制
        # 确保输出目录存在
        os.makedirs("aspects_outputs", exist_ok=True)

    def should_continue(self, node_content: str, current_depth: int) -> bool:
        """LLM 判断当前 aspect 是否需要继续细化"""
        # 首先检查是否达到最大深度
        if current_depth >= self.max_depth:
            print(f"已达到最大深度 {self.max_depth}，停止继续细化")
            return False

        print(f"\n正在判断是否需要继续细化: {node_content}")
        prompt = f"""
You are thinking in a tree-of-thought manner.

Given the aspect: "{node_content}", decide whether it needs to be further broken down into more specific sub-aspects.

Answer only "Yes" if it needs further breakdown, or "No" if it is already specific enough.
"""

        try:
            print("正在调用 OpenAI API 判断是否需要继续细化...")
            response = self.aspect_gen.model_client.chat.completions.create(
                model=self.aspect_gen.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10,
            )
            decision = response.choices[0].message.content.strip().lower()
            print(f"判断结果: {decision}")
            return decision.startswith('yes')
        except Exception as e:
            print(f"判断是否需要继续细化时出错: {e}")
            return False

    def build_tree(self, root_content: str, max_children: int = 3):
        """递归式地构建Aspect Tree"""
        print(f"\n开始构建角度树，根节点: {root_content}")
        root = AspectNode(content=root_content)
        self._expand_node(root, max_children, current_depth=1)  # 从第1层开始
        return root

    def _expand_node(self, node: AspectNode, max_children: int, current_depth: int):
        print(f"\n当前深度: {current_depth}")  # 添加深度信息
        if not self.should_continue(node.content, current_depth):
            print(f"节点 '{node.content}' 不需要继续细化")
            return

        print(f"节点 '{node.content}' 需要继续细化")
        # 生成子 aspects
        child_aspects = self.aspect_gen.generate_aspects(node.content, level="second")[:max_children]
        children = node.expand(child_aspects)
        print(f"生成的子节点: {[child.content for child in children]}")

        for child in children:
            self._expand_node(child, max_children, current_depth + 1)  # 递归时增加深度

    def print_tree(self, node: AspectNode, level=0, output_file=None):
        if level == 0:
            line = "└── " + node.content
            print(line)
            if output_file:
                output_file.write(line + "\n")
        else:
            line = "    " * (level - 1) + "├── " + node.content
            print(line)
            if output_file:
                output_file.write(line + "\n")
        
        for i, child in enumerate(node.children):
            self.print_tree(child, level + 1, output_file)

    def save_tree_structure(self, root: AspectNode, filename: str = "tree_structure.json"):
        """保存树形结构到JSON文件"""
        def node_to_dict(node: AspectNode):
            return {
                "content": node.content,
                "children": [node_to_dict(child) for child in node.children]
            }
        
        tree_dict = node_to_dict(root)
        filepath = os.path.join("aspects_outputs", filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(tree_dict, f, ensure_ascii=False, indent=2)
        print(f"树形结构已保存到 {filepath}")

    def save_tree_paths(self, root: AspectNode, filename: str = "tree_paths.json"):
        """保存所有路径到JSON文件"""
        def collect_paths(node: AspectNode, current_path: list, paths: list):
            current_path.append(node.content)
            if not node.children:
                paths.append(current_path.copy())
            else:
                for child in node.children:
                    collect_paths(child, current_path, paths)
            current_path.pop()

        paths = []
        collect_paths(root, [], paths)
        
        filepath = os.path.join("aspects_outputs", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(paths, f, ensure_ascii=False, indent=2)
        print(f"所有路径已保存到 {filepath}")

def main():
    # 使用环境变量中的API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请在环境变量中设置 OPENAI_API_KEY")

    # 创建构建器实例
    builder = AspectTreeBuilderDynamic(api_key=api_key)
    
    # 构建树
    root = builder.build_tree("如何提高工作效率")
    
    # 打印树形结构
    print("\n树形结构：")
    builder.print_tree(root)
    
    # 保存树形结构
    builder.save_tree_structure(root)
    
    # 保存所有路径
    builder.save_tree_paths(root)

def run_tree_builder(question_id: int = None):
    """独立运行角度树生成模块的入口点"""
    print("开始运行角度树生成模块...")
    
    # 读取问题
    questions_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "questions.json")
    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
    except Exception as e:
        print(f"读取问题文件时出错: {e}")
        return
    
    # 如果没有指定问题ID，让用户选择
    if question_id is None:
        print("\n可用的问题：")
        for q in questions_data["questions"]:
            print(f"{q['id']}. {q['question']}")
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
    
    # 使用环境变量中的API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请在环境变量中设置 OPENAI_API_KEY")

    # 创建构建器实例
    builder = AspectTreeBuilderDynamic(api_key=api_key)
    
    # 构建树
    root = builder.build_tree(selected_question)
    
    # 打印树形结构
    print("\n树形结构：")
    builder.print_tree(root)
    
    # 保存树形结构
    builder.save_tree_structure(root)
    
    # 保存所有路径
    builder.save_tree_paths(root)
    
    print("角度树生成模块运行完成！")
    
    

if __name__ == "__main__":
    run_tree_builder()
