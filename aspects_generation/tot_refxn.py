from aspect_node import AspectNode
from aspect_generator import AspectGenerator
import os
import json
from typing import List, Tuple, Dict

class AspectTreeBuilderReflexion:
    def __init__(self, api_key: str, max_depth: int = 4):
        self.aspect_gen = AspectGenerator(api_key)
        self.max_depth = max_depth
        self.reflection_history: Dict[str, List[Dict]] = {}  # 存储反思历史
        os.makedirs("aspects_outputs", exist_ok=True)

    def reflect_on_aspects(self, parent_aspect: str, child_aspects: List[str], current_depth: int) -> Tuple[List[str], bool]:
        """对生成的aspects进行反思和评估"""
        print(f"\n正在反思和评估aspects: {child_aspects}")
        prompt = f"""
You are thinking in a tree-of-thought manner with self-reflection.

Given the parent aspect: "{parent_aspect}" and its potential sub-aspects:
{chr(10).join([f"- {aspect}" for aspect in child_aspects])}

Please analyze these aspects considering:
1. Fairness: Are all perspectives fairly represented?
2. Diversity: Do the aspects cover different viewpoints?
3. Balance: Is there any bias or over-representation?
4. Relevance: Are all aspects directly relevant to the parent?

Provide your analysis in the following format:
REFLECTION: [Your detailed analysis]
FAIRNESS_SCORE: [0-10]
DIVERSITY_SCORE: [0-10]
RECOMMENDATION: [Keep/Modify/Prune]
MODIFIED_ASPECTS: [If recommending modification, provide at most 5 new aspects, one per line]
"""

        try:
            response = self.aspect_gen.model_client.chat.completions.create(
                model=self.aspect_gen.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000,
            )
            
            reflection_text = response.choices[0].message.content.strip()
            
            # 解析反思结果
            reflection_lines = reflection_text.split('\n')
            reflection_dict = {}
            for line in reflection_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    reflection_dict[key.strip()] = value.strip()
            
            # 记录反思历史
            if parent_aspect not in self.reflection_history:
                self.reflection_history[parent_aspect] = []
            self.reflection_history[parent_aspect].append({
                'depth': current_depth,
                'aspects': child_aspects,
                'reflection': reflection_dict
            })
            
            # 根据反思结果决定是否保留或修改aspects
            if reflection_dict.get('RECOMMENDATION') == 'Keep':
                return child_aspects, True
            elif reflection_dict.get('RECOMMENDATION') == 'Modify':
                modified_aspects = reflection_dict.get('MODIFIED_ASPECTS', '').split('\n')
                modified_aspects = [aspect.strip() for aspect in modified_aspects if aspect.strip()]
                if modified_aspects:  # 如果有修改后的aspects，使用它们
                    return modified_aspects, True
                else:  # 如果没有提供修改后的aspects，保持原样
                    return child_aspects, True
            else:  # Prune
                return [], False
                
        except Exception as e:
            print(f"反思过程出错: {e}")
            return child_aspects, True  # 出错时默认保留

    def should_continue(self, node_content: str, current_depth: int) -> bool:
        """判断当前aspect是否需要继续细化"""
        if current_depth >= self.max_depth:
            print(f"已达到最大深度 {self.max_depth}，停止继续细化")
            return False

        print(f"\n正在判断是否需要继续细化: {node_content}")
        prompt = f"""
You are thinking in a tree-of-thought manner.

Given the aspect: "{node_content}", decide whether it needs to be further broken down into more specific sub-aspects.

Consider:
1. Is this aspect specific enough?
2. Would further breakdown add value?
3. Is there enough depth in this direction?

Answer only "Yes" if it needs further breakdown, or "No" if it is already specific enough.
"""

        try:
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

    def prune_tree(self, root: AspectNode, original_question: str):
        """对生成的树进行剪枝，删除不相关的节点"""
        print("\n开始对树进行剪枝...")
        
        def evaluate_relevance(node_content: str, parent_content: str, original_question: str) -> Tuple[float, bool]:
            """评估节点与主题的相关性"""
            prompt = f"""
You are evaluating the relevance of an aspect in a tree structure.

Original Question: "{original_question}"
Parent Aspect: "{parent_content}"
Current Aspect: "{node_content}"

Please evaluate:
1. How relevant is this aspect to the original question? (0-10)
2. Does this aspect add meaningful value to the parent aspect? (Yes/No)

Provide your evaluation in the following format:
RELEVANCE_SCORE: [0-10]
ADDS_VALUE: [Yes/No]
JUSTIFICATION: [Brief explanation]
"""
            try:
                response = self.aspect_gen.model_client.chat.completions.create(
                    model=self.aspect_gen.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200,
                )
                
                evaluation_text = response.choices[0].message.content.strip()
                evaluation_lines = evaluation_text.split('\n')
                evaluation_dict = {}
                for line in evaluation_lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        evaluation_dict[key.strip()] = value.strip()
                
                relevance_score = float(evaluation_dict.get('RELEVANCE_SCORE', '0'))
                adds_value = evaluation_dict.get('ADDS_VALUE', 'No').lower() == 'yes'
                
                # 记录评估历史
                if node_content not in self.reflection_history:
                    self.reflection_history[node_content] = []
                self.reflection_history[node_content].append({
                    'type': 'pruning_evaluation',
                    'parent': parent_content,
                    'evaluation': evaluation_dict
                })
                
                return relevance_score, adds_value
                
            except Exception as e:
                print(f"评估相关性时出错: {e}")
                return 0.0, False

        def prune_node(node: AspectNode, parent_content: str = None) -> bool:
            """递归剪枝节点"""
            if parent_content is None:
                parent_content = "ROOT"
            
            # 评估当前节点的相关性
            relevance_score, adds_value = evaluate_relevance(
                node.content,
                parent_content,
                original_question
            )
            
            # 如果相关性分数低于阈值或没有增加价值，则剪枝
            if relevance_score < 6 or not adds_value:
                print(f"剪枝节点: {node.content} (相关性分数: {relevance_score}, 增加价值: {adds_value})")
                return True
            
            # 递归处理子节点
            node.children = [
                child for child in node.children
                if not prune_node(child, node.content)
            ]
            
            return False

        # 从根节点开始剪枝
        prune_node(root)
        print("树剪枝完成")

    def build_tree(self, root_content: str, max_children: int = 3):
        """递归式地构建Aspect Tree，包含反思机制和剪枝"""
        print(f"\n开始构建角度树，根节点: {root_content}")
        root = AspectNode(content=root_content)
        self._expand_node(root, max_children, current_depth=1)
        
        # 在树构建完成后进行剪枝
        self.prune_tree(root, root_content)
        return root

    def _expand_node(self, node: AspectNode, max_children: int, current_depth: int):
        print(f"\n当前深度: {current_depth}")
        if not self.should_continue(node.content, current_depth):
            print(f"节点 '{node.content}' 不需要继续细化")
            return

        print(f"节点 '{node.content}' 需要继续细化")
        # 生成子aspects
        child_aspects = self.aspect_gen.generate_aspects(node.content, level="second")[:max_children]
        
        # 对生成的aspects进行反思
        reflected_aspects, should_continue = self.reflect_on_aspects(
            node.content, 
            child_aspects, 
            current_depth
        )
        
        if not should_continue:
            print(f"节点 '{node.content}' 经过反思后决定剪枝")
            return
            
        if reflected_aspects:
            children = node.expand(reflected_aspects)
            print(f"经过反思后的子节点: {[child.content for child in children]}")
            
            for child in children:
                self._expand_node(child, max_children, current_depth + 1)

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

    def save_tree_structure(self, root: AspectNode, filename: str = "tree_structure_reflexion.json"):
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

    def save_tree_paths(self, root: AspectNode, filename: str = "tree_paths_reflexion.json"):
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

    def save_reflection_history(self, filename: str = "reflection_history.json"):
        """保存反思历史到JSON文件"""
        filepath = os.path.join("aspects_outputs", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.reflection_history, f, ensure_ascii=False, indent=2)
        print(f"反思历史已保存到 {filepath}")

def main():
    # 使用环境变量中的API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请在环境变量中设置 OPENAI_API_KEY")

    # 创建构建器实例
    builder = AspectTreeBuilderReflexion(api_key=api_key)
    
    # 构建树
    root = builder.build_tree("如何提高工作效率")
    
    # 打印树形结构
    print("\n树形结构：")
    builder.print_tree(root)
    
    # 保存树形结构
    builder.save_tree_structure(root)
    
    # 保存所有路径
    builder.save_tree_paths(root)
    
    # 保存反思历史
    builder.save_reflection_history()

def run_tree_builder_reflexion(question_id: int = None):
    """独立运行带有反思机制的角度树生成模块的入口点"""
    print("开始运行带有反思机制的角度树生成模块...")
    
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
    builder = AspectTreeBuilderReflexion(api_key=api_key)
    
    # 构建树
    root = builder.build_tree(selected_question)
    
    # 打印树形结构
    print("\n树形结构：")
    builder.print_tree(root)
    
    # 保存树形结构
    builder.save_tree_structure(root)
    
    # 保存所有路径
    builder.save_tree_paths(root)
    
    # 保存反思历史
    builder.save_reflection_history()
    
    print("带有反思机制的角度树生成模块运行完成！")

if __name__ == "__main__":
    run_tree_builder_reflexion()
