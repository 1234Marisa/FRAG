from aspect_node import AspectNode
from aspect_generator import AspectGenerator
import os
import json
from typing import List, Tuple, Dict


#python run.py ../data/ultrachat_200k/short_prompt_ultrachat_200k_train_gen.jsonl 1
class AspectTreeBuilderReflexion:
    def __init__(self, api_key: str, max_depth: int = 3):
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
MODIFIED_ASPECTS: [If recommending modification, provide at most 3 new aspects, one per line]
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
                # 即使建议剪枝，也保留至少一个最相关的aspect
                if len(child_aspects) > 1:
                    return [child_aspects[0]], True
                return child_aspects, True
                
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

    def evaluate_relevance(self, node_content: str, parent_content: str, original_question: str, current_depth: int, sibling_aspects: List[str] = None, path_to_root: List[str] = None) -> Tuple[float, bool]:
        """评估节点与主题的相关性"""
        # 获取当前节点的所有兄弟节点
        if sibling_aspects is None:
            sibling_aspects = []
        if path_to_root is None:
            path_to_root = []
        
        # 构建从根节点到当前节点的路径
        path_str = " -> ".join(path_to_root + [node_content])
        
        prompt = f"""
You are evaluating the relevance of an aspect in a tree structure.

Original Question: "{original_question}"
Current Depth: {current_depth}

Complete Path from Root:
{path_str}

Parent Aspect: "{parent_content}"
Current Aspect: "{node_content}"

Sibling Aspects at this level:
{chr(10).join([f"- {aspect}" for aspect in sibling_aspects])}

Please evaluate considering:
1. How relevant is this aspect to the original question? (0-10)
2. Does this aspect add meaningful value to the parent aspect? (Yes/No)
3. How does this aspect complement or differ from its siblings?
4. Is there any redundancy with existing aspects?
5. How well does this aspect fit into the overall path from root?

Provide your evaluation in the following format:
RELEVANCE_SCORE: [0-10]
ADDS_VALUE: [Yes/No]
COMPLEMENTARITY: [High/Medium/Low]
REDUNDANCY: [Yes/No]
PATH_COHERENCE: [High/Medium/Low]
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
            complementarity = evaluation_dict.get('COMPLEMENTARITY', 'Low')
            has_redundancy = evaluation_dict.get('REDUNDANCY', 'No').lower() == 'yes'
            path_coherence = evaluation_dict.get('PATH_COHERENCE', 'Low')
            
            # 记录评估历史
            if node_content not in self.reflection_history:
                self.reflection_history[node_content] = []
            self.reflection_history[node_content].append({
                'type': 'pruning_evaluation',
                'parent': parent_content,
                'depth': current_depth,
                'siblings': sibling_aspects,
                'path_to_root': path_to_root,
                'evaluation': evaluation_dict
            })
            
            # 如果存在冗余，降低相关性分数
            if has_redundancy:
                relevance_score *= 0.8
            
            # 根据互补性调整分数
            if complementarity == 'High':
                relevance_score *= 1.2
            elif complementarity == 'Low':
                relevance_score *= 0.8
            
            # 根据路径连贯性调整分数
            if path_coherence == 'High':
                relevance_score *= 1.2
            elif path_coherence == 'Low':
                relevance_score *= 0.8
            
            return relevance_score, adds_value
            
        except Exception as e:
            print(f"评估相关性时出错: {e}")
            return 0.0, False

    def prune_tree(self, root: AspectNode, original_question: str):
        """对生成的树进行剪枝，删除不相关的节点"""
        print("\n开始对树进行剪枝...")
        self.original_question = original_question
        self._prune_node(root)

    def _prune_node(self, node: AspectNode, parent_content: str = None, current_depth: int = 0, path_to_root: List[str] = None) -> bool:
        """递归剪枝节点"""
        if parent_content is None:
            parent_content = "ROOT"
        if path_to_root is None:
            path_to_root = []
        
        # 获取当前节点的所有兄弟节点
        sibling_aspects = []
        if node.parent:
            sibling_aspects = [child.content for child in node.parent.children if child != node]
        
        # 构建到当前节点的路径
        current_path = path_to_root + [node.content]
        
        # 评估当前节点的相关性
        relevance_score, adds_value = self.evaluate_relevance(
            node.content,
            parent_content,
            self.original_question,
            current_depth,
            sibling_aspects,
            path_to_root
        )
        
        # 提高剪枝阈值到7
        if relevance_score < 7 or not adds_value:
            print(f"剪枝节点: {node.content} (相关性分数: {relevance_score}, 增加价值: {adds_value})")
            return True
        
        # 递归处理子节点
        node.children = [
            child for child in node.children
            if not self._prune_node(child, node.content, current_depth + 1, current_path)
        ]
        
        return False

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

    def save_tree_structure(self, root: AspectNode, filename: str = "tree_structure.json"):
        """保存树形结构到JSON文件"""
        tree_dict = self._node_to_dict(root)
        filepath = os.path.join(filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(tree_dict, f, ensure_ascii=False, indent=2)
        print(f"树形结构已保存到 {filepath}")

    def save_tree_paths(self, root: AspectNode, filename: str = "paths.json"):
        """保存所有路径到JSON文件"""
        paths = self._collect_paths(root, [], [])
        filepath = os.path.join(filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(paths, f, ensure_ascii=False, indent=2)
        print(f"所有路径已保存到 {filepath}")

    def save_reflection_history(self, filename: str = "reflection_history.json"):
        """保存反思历史到JSON文件"""
        filepath = os.path.join(filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.reflection_history, f, ensure_ascii=False, indent=2)
        print(f"反思历史已保存到 {filepath}")

    def process_jsonl_questions(self, jsonl_path: str, num_questions: int = 10):
        """处理JSONL文件中的问题并生成aspects树"""
        print(f"开始处理JSONL文件: {jsonl_path}")
        
        # 读取JSONL文件
        questions = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= num_questions:
                    break
                try:
                    data = json.loads(line)
                    if 'prompt' in data:
                        questions.append(data['prompt'])
                except json.JSONDecodeError:
                    print(f"跳过无效的JSON行: {line.strip()}")
        
        # 为每个问题生成aspects树
        results = []
        for i, question in enumerate(questions, 1):
            print(f"\n处理问题 {i}/{len(questions)}: {question}")
            
            # 保存原始问题
            self.original_question = question
            
            # 构建树
            root = self.build_tree(question)
            
            # 收集结果
            result = {
                'question': question,
                'tree_structure': self._node_to_dict(root),
                'paths': self._collect_paths(root, [], []),
                'reflection_history': self.reflection_history
            }
            results.append(result)
            
            # 保存单个问题的结果
            output_dir = os.path.join("aspects_outputs", f"question_{i}")
            os.makedirs(output_dir, exist_ok=True)
            
            # 使用类的方法保存结果
            self.save_tree_structure(root, os.path.join(output_dir, "tree_structure.json"))
            self.save_tree_paths(root, os.path.join(output_dir, "paths.json"))
            self.save_reflection_history(os.path.join(output_dir, "reflection_history.json"))
            
            # 清空反思历史，为下一个问题做准备
            self.reflection_history = {}
        
        # 保存所有结果到一个文件
        with open(os.path.join("aspects_outputs", "all_results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n处理完成！结果已保存到 aspects_outputs 目录")

    def _node_to_dict(self, node: AspectNode):
        """将节点转换为字典格式"""
        return {
            "content": node.content,
            "children": [self._node_to_dict(child) for child in node.children]
        }

    def _collect_paths(self, node: AspectNode, current_path: list, paths: list):
        """收集所有路径"""
        current_path.append(node.content)
        if not node.children:
            paths.append(current_path.copy())
        else:
            for child in node.children:
                self._collect_paths(child, current_path, paths)
        current_path.pop()
        return paths
