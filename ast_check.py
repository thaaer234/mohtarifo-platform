import ast

with open("dashboard/views.py", "r", encoding="utf-8") as f:
    tree = ast.parse(f.read(), filename="dashboard/views.py")

class AssignmentFinder(ast.NodeVisitor):
    def __init__(self):
        self.in_admin_billing = False

    def visit_FunctionDef(self, node):
        if node.name == 'admin_billing':
            self.in_admin_billing = True
            print(f"Found FunctionDef: {node.name} at line {node.lineno}")
            self.generic_visit(node)
            self.in_admin_billing = False
        else:
            self.generic_visit(node)

    def visit_Assign(self, node):
        if self.in_admin_billing:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'actual_earned_cents':
                    print(f"  Assignment at line {node.lineno}: target={target.id}, value={ast.dump(node.value)}")
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        if self.in_admin_billing:
            if isinstance(node.target, ast.Name) and node.target.id == 'actual_earned_cents':
                print(f"  AugAssignment at line {node.lineno}: target={node.target.id}, op={type(node.op).__name__}, value={ast.dump(node.value)}")
        self.generic_visit(node)

AssignmentFinder().visit(tree)
