# Pulse AST (Abstract Snytax Tree)

# CORE AST
class AST(object):
    _nodes = { }

    @classmethod
    def __init_subclass__(cls):
        AST._nodes[cls.__name__] = cls

        if not hasattr(cls, '__annotations__'):
            return

        fields = list(cls.__annotations__.items())

        def __init__(self, *args, **kwargs):
            if len(args) != len(fields):
                raise TypeError(f'Expected {len(fields)} arguments')
            for (name, ty), arg in zip(fields, args):
                if isinstance(ty, list):
                    if not isinstance(arg, list):
                        raise TypeError(f'{name} must be list')
                    if not all(isinstance(item, ty[0]) for item in arg):
                        raise TypeError(f'All items of {name} must be {ty[0]}')
                elif not isinstance(arg, ty):
                    raise TypeError(f'{name} must be {ty}')
                setattr(self, name, arg)

            for name, val in kwargs.items():
                setattr(self, name, val)

        cls.__init__ = __init__
        cls._fields = [name for name,_ in fields]

    def __repr__(self):
        vals = [ getattr(self, name) for name in self._fields ]
        argstr = ', '.join(f'{name}={type(val).__name__ if isinstance(val, AST) else repr(val)}'
                           for name, val in zip(self._fields, vals))
        return f'{type(self).__name__}({argstr})'

# AST NODES
class Statement(AST):
    pass

class Expression(AST):
    pass

class Literal(Expression):
    pass

class DataType(AST):
    pass

class Location(AST):
    pass

class PrintStatement(Statement):
    value : Expression

class IntegerLiteral(Literal):
    value : int

class FloatLiteral(Literal):
    value : float

class CharLiteral(Literal):
    value : str

class BoolLiteral(Literal):
    value : str

class IfStatement(Statement):
    condition : Expression
    true_block : [Statement]
    false_block : [Statement]

class WhileStatement(Statement):
    condition : Expression
    body : [Statement]

class BinOp(Expression):
    op    : str
    left  : Expression
    right : Expression

class UnaryOp(Expression):
    op    : str
    right : Expression

class FuncCall(Expression):
    name      : str
    arguments : [Expression]

class ConstDeclaration(Statement):
    name  : str
    value : Expression

class FuncParameter(AST):
    name: str
    datatype: DataType

class FuncDeclaration(Statement):
    name  : str
    params : [FuncParameter]
    datatype: DataType
    body : [Statement]

class ReturnStatement(Statement):
    value: Expression

class SimpleType(DataType):
    name : str

class VarDeclaration(Statement):
    name     : str
    datatype : DataType
    value    : (Expression, type(None))

class SimpleLocation(Location):
    name : str

class ReadLocation(Expression):
    location: Location

class WriteLocation(Statement):
    location: Location
    value : Expression

# taken from python's ast module
class NodeVisitor(object):
    def visit(self, node):
        if isinstance(node, list):
            for item in node:
                self.visit(item)
        elif isinstance(node, AST):
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            visitor(node)

    def generic_visit(self,node):
        for field in getattr(node, '_fields'):
            value = getattr(node, field, None)
            self.visit(value)

    @classmethod
    def __init_subclass__(cls):
        for key in vars(cls):
            if key.startswith('visit_'):
                assert key[6:] in globals(), f"{key} doesn't match any AST node"

def flatten(top):
    class Flattener(NodeVisitor):
        def __init__(self):
            self.depth = 0
            self.nodes = []
        def generic_visit(self, node):
            self.nodes.append((self.depth, node))
            self.depth += 1
            NodeVisitor.generic_visit(self, node)
            self.depth -= 1

    d = Flattener()
    d.visit(top)
    return d.nodes
