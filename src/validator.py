# Pulse semantics checker and validator

from collections import ChainMap
from error import error
from ast import *
from type import *

class CheckProgramVisitor(NodeVisitor):

    def __init__(self):
        self.symbols = {}
        self.temp_symbols = { }
        self.expected_ret_type = None
        self.current_ret_type = None
        self.functions = { }
        self.keywords = {t.name for t in Type.__subclasses__()}
        self.recursion = None

    def visit_VarDeclaration(self, node):
        node.type = None

        if node.name in self.keywords:
            error(node.lineno, f"Name '{node.name}' is not a legal name for variable declaration")
            return

        if node.name not in self.symbols:
            self.visit(node.datatype)

            if node.datatype.type:
                if node.value:
                    self.visit(node.value)

                    if node.value.type:
                        if node.value.type == node.datatype.type:
                            node.type = node.datatype.type
                            self.symbols[node.name] = node
                        else:
                            error(node.lineno,
                                  f"Declaring variable '{node.name}' of type '{node.datatype.type.name}' but assigned expression of type '{node.value.type.name}'")
                else:
                    node.type = node.datatype.type
                    self.symbols[node.name] = node
            else:
                error(node.lineno, f"Unknown type '{node.datatype.name}'")
        else:
            prev_lineno = self.symbols[node.name].lineno
            error(node.lineno, f"Name '{node.name}' has already been defined at line {prev_lineno}")

    def visit_ConstDeclaration(self, node):
        if node.name not in self.symbols:
            self.visit(node.value)
            node.type = node.value.type
            self.symbols[node.name] = node
        else:
            prev_lineno = self.symbols[node.name].lineno
            error(node.lineno, f"Name '{node.name}' has already been defined at line {prev_lineno}")

    def visit_IntegerLiteral(self, node):
        node.type = IntType

    def visit_FloatLiteral(self, node):
        node.type = FloatType

    def visit_CharLiteral(self, node):
        node.type = CharType

    def visit_BoolLiteral(self, node):
        node.type = BoolType

    def visit_PrintStatement(self, node):
        self.visit(node.value)

    def visit_IfStatement(self, node):
        self.visit(node.condition)

        cond_type = node.condition.type
        if cond_type:
            if issubclass(node.condition.type, BoolType):
                self.visit(node.true_block)
                self.visit(node.false_block)
            else:
                error(node.lineno, f"'Condition must be of type 'bool' but got type '{cond_type.name}'")

    def visit_WhileStatement(self, node):
        self.visit(node.condition)

        cond_type = node.condition.type
        if cond_type:
            if issubclass(node.condition.type, BoolType):
                self.visit(node.body)
            else:
                error(node.lineno, f"'Condition must be of type 'bool' but got type '{cond_type.name}'")

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.right)

        node.type = None
        if node.left.type and node.right.type:
            op_type = node.left.type.binop_type(node.op, node.right.type)
            if not op_type:
                left_tname = node.left.type.name
                right_tname = node.right.type.name
                error(node.lineno, f"Binary operation '{left_tname} {node.op} {right_tname}' not supported")

            node.type = op_type

    def visit_UnaryOp(self, node):
        self.visit(node.right)

        node.type = None
        if node.right.type:
            op_type = node.right.type.unaryop_type(node.op)
            if not op_type:
                right_tname = node.right.type.name
                error(node.lineno, f"Unary operation '{node.op} {right_tname}' not supported")

            node.type = op_type

    def visit_WriteLocation(self, node):
        self.visit(node.location)
        self.visit(node.value)

        node.type = None
        if node.location.type and node.value.type:
            loc_name = node.location.name

            if isinstance(self.symbols[loc_name], ConstDeclaration):
                error(node.lineno, f"Cannot write to constant '{loc_name}'")
                return

            if node.location.type == node.value.type:
                node.type = node.value.type
            else:
                error(node.lineno,
                      f"Cannot assign type '{node.value.type.name}' to variable '{node.location.name}' of type '{node.location.type.name}'")

    def visit_ReadLocation(self, node):
        self.visit(node.location)
        node.type = node.location.type

    def visit_SimpleLocation(self, node):
        if node.name not in self.symbols:
            node.type = None
            error(node.lineno, f"Name '{node.name}' was not defined")
        else:
            node.type = self.symbols[node.name].type

    def visit_SimpleType(self, node):
        node.type = Type.get_by_name(node.name)
        if node.type is None:
            error(node.lineno, f"Invalid type '{node.name}'")

    def visit_FuncParameter(self, node):
        self.visit(node.datatype)
        node.type = node.datatype.type

    def visit_ReturnStatement(self, node):
        self.visit(node.value)
        if self.expected_ret_type:
            self.current_ret_type = node.value.type
            if node.value.type and node.value.type != self.expected_ret_type:
                error(node.lineno, f"Function returns '{self.expected_ret_type.name}' but return statement value is of type '{node.value.type.name}'")
        else:
            error(node.lineno, "Return statement must be within a function")

    def visit_FuncDeclaration(self, node):
        if node.name in self.functions:
            prev_def = self.functions[node.name].lineno
            error(node.lineno, f"Function '{node.name}' already defined at line {prev_def}")

        self.visit(node.params)

        param_types_ok = all((param.type is not None for param in node.params))
        param_names = [param.name for param in node.params]
        param_names_ok = len(param_names) == len(set(param_names))
        if not param_names_ok:
            error(node.lineno, "Duplicate parameter names at function definition")

        self.visit(node.datatype)
        ret_type_ok = node.datatype.type is not None

        if self.temp_symbols:
            error(node.lineno, f"Illegal nested function declaration '{node.name}'")
        else:
            self.temp_symbols = self.symbols
            self.symbols = ChainMap(
                {param.name: param for param in node.params},
                self.temp_symbols
            )

            self.expected_ret_type = node.datatype.type

            self.recursion = node
            self.visit(node.body)

            if not self.current_ret_type:
                error(node.lineno, f"Function '{node.name}' has no return statement")
            elif self.current_ret_type == self.expected_ret_type:
                self.functions[node.name] = node

            self.symbols = self.temp_symbols
            self.temp_symbols = { }
            self.expected_ret_type = None
            self.current_ret_type = None
            self.recursion = None

    def visit_FuncCall(self, node):
        if node.name not in self.functions and node.name != self.recursion.name:
            error(node.lineno, f"Function '{node.name}' is not declared")
        else:
            self.visit(node.arguments)

            arg_types = tuple([arg.type.name for arg in node.arguments])
            
            if node.name == self.recursion.name:
                func = self.recursion
            else:
                func = self.functions[node.name]
                
            expected_types = tuple([param.type.name for param in func.params])
            if arg_types != expected_types:
                error(node.lineno, f"Function '{node.name}' expects {expected_types}, but was called with {arg_types}")

            node.type = func.datatype.type

def check_program(ast):
    checker = CheckProgramVisitor()
    checker.visit(ast)

def main():
    import sys
    from .parser import parse

    if len(sys.argv) < 2:
        raise SystemExit(1)

    ast = parse(open(sys.argv[1]).read())
    check_program(ast)
    if '--show-types' in sys.argv:
        for depth, node in flatten(ast):
            print('%s: %s%s type: %s' % (getattr(node, 'lineno', None), ' '*(4*depth), node,
                                         getattr(node, 'type', None)))

if __name__ == '__main__':
    main()
