# Pulse ircode - turns AST into machine code

from collections import ChainMap
import ast

IR_TYPE_MAPPING = {
    'int': 'I',
    'float': 'F',
    'char': 'B',
    'bool': 'I'
}

OP_CODES = ChainMap(
    {
        'mov': 'MOV',
        '+': 'ADD',
        '-': 'SUB',
        '*': 'MUL',
        '/': 'DIV',
        '&&': 'AND',
        '||': 'OR',
        'print': 'PRINT',
        'store': 'STORE',
        'var': 'VAR',
        'alloc': 'ALLOC',
        'load': 'LOAD',
        'label': 'LABEL',
        'cbranch': 'CBRANCH',
        'branch': 'BRANCH',
        'call': 'CALL',
        'ret': 'RET'
    },
    dict.fromkeys(['<', '>', '<=', '>=', '=', '!='], "CMP")
)

def get_op_code(operation, type_name=None):
    op_code = OP_CODES[operation]
    suffix = "" if not type_name else IR_TYPE_MAPPING[type_name]

    return f"{op_code}{suffix}"


class Function():
    def __init__(self, func_name, parameters, return_type):
        self.name = func_name
        self.parameters = parameters
        self.return_type = return_type

        self.code = []

    def append(self, ir_instruction):
        self.code.append(ir_instruction)

    def __iter__(self):
        return self.code.__iter__()

    def __repr__(self):
        params = [f"{pname}:{ptype}" for pname, ptype in self.parameters]
        return f"{self.name}({params}) -> {self.return_type}"


class GenerateCode(ast.NodeVisitor):
    def __init__(self):
        self.register_count = 0

        self.label_count = 0

        init_function = Function("__pulse_init", [], IR_TYPE_MAPPING['int'])

        self.functions = [ init_function ]

        self.code = init_function.code

        self.global_scope = True

    def new_register(self):
         self.register_count += 1
         return f'R{self.register_count}'

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"


    def visit_IntegerLiteral(self, node):
        target = self.new_register()
        op_code = get_op_code('mov', 'int')
        self.code.append((op_code, node.value, target))
        node.register = target

    def visit_FloatLiteral(self, node):
        target = self.new_register()
        op_code = get_op_code('mov', 'float')
        self.code.append((op_code, node.value, target))
        node.register = target

    def visit_CharLiteral(self, node):
        target = self.new_register()
        op_code = get_op_code('mov', 'char')
        self.code.append((op_code, ord(node.value), target))
        node.register = target

    def visit_BoolLiteral(self, node):
        target = self.new_register()
        op_code = get_op_code('mov', 'bool')
        value = 1 if node.value == "true" else 0
        self.code.append((op_code, value, target))
        node.register = target

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.right)
        operator = node.op

        op_code = get_op_code(operator, node.left.type.name)

        target = self.new_register()
        if op_code.startswith('CMP'):
            inst = (op_code, operator, node.left.register, node.right.register, target)
        else:
            inst = (op_code, node.left.register, node.right.register, target)

        self.code.append(inst)
        node.register = target

    def visit_UnaryOp(self, node):
        self.visit(node.right)
        operator = node.op

        if operator == "-":
            sub_op_code = get_op_code(operator, node.type.name)
            mov_op_code = get_op_code('mov', node.type.name)

            zero_target = self.new_register()
            zero_inst = (mov_op_code, 0, zero_target)
            self.code.append(zero_inst)

            target = self.new_register()
            inst = (sub_op_code, zero_target, node.right.register, target)
            self.code.append(inst)
            node.register = target
        elif operator == "!":
            mov_op_code = get_op_code('mov', node.type.name)
            one_target = self.new_register()
            one_inst = (mov_op_code, 1, one_target)
            self.code.append(one_inst)

            target = self.new_register()
            inst = ('XOR', one_target, node.right.register, target)
            self.code.append(inst)
            node.register = target
        else:
            node.register = node.right.register

    def visit_PrintStatement(self, node):
        self.visit(node.value)
        op_code = get_op_code('print', node.value.type.name)
        inst = (op_code, node.value.register)
        self.code.append(inst)

    def visit_ReadLocation(self, node):
        op_code = get_op_code('load', node.location.type.name)
        register = self.new_register()
        inst = (op_code, node.location.name, register)
        self.code.append(inst)
        node.register = register

    def visit_WriteLocation(self, node):
        self.visit(node.value)
        op_code = get_op_code('store', node.location.type.name)
        inst = (op_code, node.value.register, node.location.name)
        self.code.append(inst)

    def visit_ConstDeclaration(self, node):
        self.visit(node.value)

        op_code = get_op_code('var', node.type.name)
        inst = (op_code, node.name)
        self.code.append(inst)

        op_code = get_op_code('store', node.type.name)
        inst = (op_code, node.value.register, node.name)
        self.code.append(inst)

    def visit_VarDeclaration(self, node):
        self.visit(node.datatype)

        op_code = get_op_code('var' if self.global_scope else 'alloc', node.type.name)
        def_inst = (op_code, node.name)

        if node.value:
            self.visit(node.value)
            self.code.append(def_inst)
            op_code = get_op_code('store', node.type.name)
            inst = (op_code, node.value.register, node.name)
            self.code.append(inst)
        else:
            self.code.append(def_inst)

    def visit_IfStatement(self, node):
        self.visit(node.condition)

        f_label = self.new_label()
        t_label = self.new_label()
        merge_label = self.new_label()
        lbl_op_code = get_op_code('label')

        cbranch_op_code = get_op_code('cbranch')
        self.code.append((cbranch_op_code, node.condition.register, t_label, f_label))

        self.code.append((lbl_op_code, t_label))
        self.visit(node.true_block)

        branch_op_code = get_op_code('branch')
        self.code.append((branch_op_code, merge_label))


        self.code.append((lbl_op_code, f_label))
        self.visit(node.false_block)
        self.code.append((branch_op_code, merge_label))

        self.code.append((lbl_op_code, merge_label))

    def visit_WhileStatement(self, node):
        top_label = self.new_label()
        start_label = self.new_label()
        merge_label = self.new_label()
        lbl_op_code = get_op_code('label')
        branch_op_code = get_op_code('branch')


        self.code.append((branch_op_code, top_label))
        self.code.append((lbl_op_code, top_label))
        self.visit(node.condition)
        cbranch_op_code = get_op_code('cbranch')
        self.code.append((cbranch_op_code, node.condition.register, start_label, merge_label))

        self.code.append((lbl_op_code, start_label))
        self.visit(node.body)

        self.code.append((branch_op_code, top_label))

        self.code.append((lbl_op_code, merge_label))

    def visit_FuncDeclaration(self, node):
        func = Function(node.name,
                        [(p.name, IR_TYPE_MAPPING[p.datatype.type.name])
                         for p in node.params],
                        IR_TYPE_MAPPING[node.datatype.type.name])
        self.functions.append(func)

        if func.name == "main":
            func.name = "__pulse_main"

        old_code = self.code
        self.code = func.code

        self.global_scope = False
        self.visit(node.body)
        self.global_scope = True

        self.code = old_code

    def visit_FuncCall(self, node):
        self.visit(node.arguments)
        target = self.new_register()
        op_code = get_op_code('call')
        registers = [arg.register for arg in node.arguments]
        self.code.append((op_code, node.name, *registers, target))
        node.register = target

    def visit_ReturnStatement(self, node):
        self.visit(node.value)
        op_code = get_op_code('ret')
        self.code.append((op_code, node.value.register))
        node.register = node.value.register


def compile_ircode(source):
    from parser import parse
    from validator import check_program
    from error import errors_reported

    ast = parse(source)
    check_program(ast)

    if not errors_reported():
        gen = GenerateCode()
        gen.visit(ast)
        return gen.functions
    else:
        return []

def main():
    import sys

    if len(sys.argv) != 2:
        raise SystemExit(1)

    source = open(sys.argv[1]).read()
    code = compile_ircode(source)

    for f in code :
        print(f'{"::"*5} {f} {"::"*5}')
        for instruction in f.code:
            print(instruction)
        print("*"*30)

if __name__ == '__main__':
    main()
