# Pulse tokenizer / lexer

from error import error
from sly import Lexer

class PulseLexer(Lexer):
    tokens = {
        'PRINT', 'CONST', 'ELSE', 'EXTERN', 'FUNCTION', 'IF', 'RETURN', 'WHILE', 'VAR',
        'ID',
        'INTEGER', 'FLOAT', 'CHAR', 'BOOL',
        'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'ASSIGN', 'SEMI', 'COMA',
        'LE', 'LT', 'GE', 'GT', 'EQ', 'NE', 'AND', 'OR', 'NOT',
        'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
    }

    ignore = ' \t\r'

    @_(r'/\*(.|\n)*?\*/')
    def BLOCK_COMMENT(self, token):
        self.lineno += token.value.count('\n')
        return None

    @_(r'//.*')
    def LINE_COMMENT(self, token):
        return None

    @_(r'\n+')
    def NEWLINE(self, token):
        self.lineno += token.value.count('\n')

    PLUS = r'\+'
    MINUS = r'-'
    TIMES = r'\*'
    DIVIDE = r'/'
    ASSIGN = r'<-'
    SEMI = r';'
    COMA = r','
    LPAREN = r'\('
    RPAREN = r'\)'

    LE = r'<='
    LT = r'<'
    GE = r'>='
    GT = r'>'
    EQ = r'='
    NE = r'!='
    AND = r'&&'
    OR = r'\|\|'
    NOT = r'!'

    LBRACE = r'{'
    RBRACE = r'}'

    FLOAT = r'(((\d+\.\d*)|(\.\d+))([eE][+-]?\d+)?)|(\d+[eE][+-]?\d+)'

    INTEGER = r'(0x[0-9ABCDEF]+)|(0b[01]+)|(0o[0-5]+)|\d+'

    CHAR = r"'((\\n)|(\\x[0-9a-f]{2})|(\\')|(\\\\)|.)'"

    BOOL = r'(true)|(false)'

    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def ID(self, t):
        keywords = {
            'const',
            'else',
            'extern',
            'function',
            'if',
            'print',
            'return',
            'while',
            'var'
        }
        if t.value in keywords:
            t.type = t.value.upper()
        return t

    def error(self, t):
        error(self.lineno,"Illegal character %r" % t.value[0])
        self.index += 1

def main():
    import sys

    if len(sys.argv) != 2:
        raise SystemExit(1)

    lexer = PulseLexer()
    text = open(sys.argv[1]).read()
    for tok in lexer.tokenize(text):
        print(tok)

if __name__ == '__main__':
    main()

