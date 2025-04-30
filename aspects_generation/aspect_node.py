# generation/aspect_node.py

class AspectNode:
    def __init__(self, content: str, parent=None):
        self.content = content  # 当前这个节点代表的 aspect
        self.parent = parent    # 父节点
        self.children = []      # 子节点列表

    def expand(self, children_contents: list):
        """根据子内容，扩展出子节点"""
        for child_content in children_contents:
            child_node = AspectNode(content=child_content, parent=self)
            self.children.append(child_node)
        return self.children

    def get_path(self):
        """回溯路径（从当前节点到根节点）"""
        path = []
        node = self
        while node:
            path.append(node.content)
            node = node.parent
        return path[::-1]  # 从根节点到当前节点的顺序返回
