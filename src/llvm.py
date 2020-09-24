# Pulse llvmgen -> turns intermediate code to llvm ir
from collections import ChainMap
from functools import partialmethod

from llvmlite.ir import (
    Module, IRBuilder, Function, IntType, DoubleType, VoidType, Constant,
    GlobalVariable, FunctionType
    )


int_type    = IntType(32)         # 32-bit integer
float_type  = DoubleType()        # 64-bit float
byte_type   = IntType(8)          # 8-bit integer

void_type   = VoidType()          # Void type.  This is a special type
                                  # used for internal functions returning
                                  # no value

LLVM_TYPE_MAPPING = {
    'I': int_type,
    'F': float_type,
    'B': byte_type,
    None: void_type
}

class GenerateLLVM(object):
    def __init__(self):
        self.module = Module('module')
        self.globals = { }
        self.blocks = { }
        self.declare_runtime_library()


    def declare_runtime_library(self):
        self.runtime = {}

        self.runtime['_print_int'] = Function(self.module,
                                              FunctionType(void_type, [int_type]),
                                              name="_print_int")

        self.runtime['_print_float'] = Function(self.module,
                                                FunctionType(void_type, [float_type]),
                                                name="_print_float")

        self.runtime['_print_byte'] = Function(self.module,
                                                FunctionType(void_type, [byte_type]),
                                                name="_print_byte")

    def generate_code(self, ir_function):
        self.function = Function(self.module,
                                 FunctionType(
                                     LLVM_TYPE_MAPPING[ir_function.return_type],
                                     [LLVM_TYPE_MAPPING[ptype] for _, ptype in ir_function.parameters]
                                 ),
                                 name=ir_function.name)

        self.block = self.function.append_basic_block('entry')
        self.builder = IRBuilder(self.block)

        self.globals[ir_function.name] = self.function

        self.locals = { }

        self.vars = ChainMap(self.locals, self.globals)

        self.temps = { }

        for n, (pname, ptype) in enumerate(ir_function.parameters):
            self.vars[pname] = self.builder.alloca(LLVM_TYPE_MAPPING[ptype], name=pname)
            self.builder.store(self.function.args[n], self.vars[pname])

        if ir_function.return_type:
            self.vars['return'] = self.builder.alloca(
                LLVM_TYPE_MAPPING[ir_function.return_type], name='return')
        self.return_block = self.function.append_basic_block('return')

        for opcode, *args in ir_function.code:
            if hasattr(self, 'emit_'+opcode):
                getattr(self, 'emit_'+opcode)(*args)
            else:
                print('Warning: No emit_'+opcode+'() method')

        if not self.block.is_terminated:
            self.builder.branch(self.return_block)

        self.builder.position_at_end(self.return_block)
        self.builder.ret(self.builder.load(self.vars['return'], 'return'))

    def get_block(self, block_name):
        block = self.blocks.get(block_name)
        if block is None:
            block = self.function.append_basic_block(block_name)
            self.blocks[block_name] = block

        return block

    def emit_MOV(self, value, target, val_type):
        self.temps[target] = Constant(val_type, value)

    emit_MOVI = partialmethod(emit_MOV, val_type=int_type)
    emit_MOVF = partialmethod(emit_MOV, val_type=float_type)
    emit_MOVB = partialmethod(emit_MOV, val_type=byte_type)

    def emit_VAR(self, name, var_type):
        var = GlobalVariable(self.module, var_type, name=name)
        var.initializer = Constant(var_type, 0)
        self.globals[name] = var

    emit_VARI = partialmethod(emit_VAR, var_type=int_type)
    emit_VARF = partialmethod(emit_VAR, var_type=float_type)
    emit_VARB = partialmethod(emit_VAR, var_type=byte_type)

    def emit_ALLOC(self, name, var_type):
        self.locals[name] = self.builder.alloca(var_type, name=name)

    emit_ALLOCI = partialmethod(emit_ALLOC, var_type=int_type)
    emit_ALLOCF = partialmethod(emit_ALLOC, var_type=float_type)
    emit_ALLOCB = partialmethod(emit_ALLOC, var_type=byte_type)

    def emit_LOADI(self, name, target):
        self.temps[target] = self.builder.load(self.vars[name], name=target)

    emit_LOADF = emit_LOADI
    emit_LOADB = emit_LOADI

    def emit_STOREI(self, source, target):
        self.builder.store(self.temps[source], self.vars[target])

    emit_STOREF = emit_STOREI
    emit_STOREB = emit_STOREI

    def emit_ADDI(self, left, right, target):
        self.temps[target] = self.builder.add(self.temps[left], self.temps[right], name=target)

    def emit_ADDF(self, left, right, target):
        self.temps[target] = self.builder.fadd(self.temps[left], self.temps[right], name=target)

    def emit_SUBI(self, left, right, target):
        self.temps[target] = self.builder.sub(self.temps[left], self.temps[right], name=target)

    def emit_SUBF(self, left, right, target):
        self.temps[target] = self.builder.fsub(self.temps[left], self.temps[right], name=target)

    def emit_MULI(self, left, right, target):
        self.temps[target] = self.builder.mul(self.temps[left], self.temps[right], name=target)

    def emit_MULF(self, left, right, target):
        self.temps[target] = self.builder.fmul(self.temps[left], self.temps[right], name=target)

    def emit_DIVI(self, left, right, target):
        self.temps[target] = self.builder.sdiv(self.temps[left], self.temps[right], name=target)

    def emit_DIVF(self, left, right, target):
        self.temps[target] = self.builder.fdiv(self.temps[left], self.temps[right], name=target)

    def emit_PRINT(self, source, runtime_name):
        self.builder.call(self.runtime[runtime_name], [self.temps[source]])

    emit_PRINTI = partialmethod(emit_PRINT, runtime_name="_print_int")
    emit_PRINTF = partialmethod(emit_PRINT, runtime_name="_print_float")
    emit_PRINTB = partialmethod(emit_PRINT, runtime_name="_print_byte")

    def emit_CMPI(self, operator, left, right, target):
        if operator == "=":
            operator = "=="
            
        tmp = self.builder.icmp_signed(operator, self.temps[left], self.temps[right], 'tmp')
        self.temps[target] = self.builder.zext(tmp, int_type, target)

    def emit_CMPF(self, operator, left, right, target):
        if operator == "=":
            operator = "=="
            
        tmp = self.builder.fcmp_ordered(operator, self.temps[left], self.temps[right], 'tmp')
        self.temps[target] = self.builder.zext(tmp, int_type, target)

    emit_CMPB = emit_CMPI

    def emit_AND(self, left, right, target):
        self.temps[target] = self.builder.and_(self.temps[left], self.temps[right], target)

    def emit_OR(self, left, right, target):
        self.temps[target] = self.builder.or_(self.temps[left], self.temps[right], target)

    def emit_XOR(self, left, right, target):
        self.temps[target] = self.builder.xor(self.temps[left], self.temps[right], target)

    def emit_LABEL(self, lbl_name):
        self.block = self.get_block(lbl_name)
        self.builder.position_at_end(self.block)

    def emit_BRANCH(self, dst_label):
        if not self.block.is_terminated:
            self.builder.branch(self.get_block(dst_label))

    def emit_CBRANCH(self, test_target, true_label, false_label):
        true_block = self.get_block(true_label)
        false_block = self.get_block(false_label)
        testvar = self.temps[test_target]
        self.builder.cbranch(self.builder.trunc(testvar, IntType(1)), true_block, false_block)

    def emit_RET(self, register):
        self.builder.store(self.temps[register], self.vars['return'])
        self.builder.branch(self.return_block)

    def emit_CALL(self, func_name, *registers):
        args = [self.temps[r] for r in registers[:-1]]
        target = registers[-1]
        self.temps[target] = self.builder.call(self.globals[func_name], args)


def compile_llvm(source):
    from ir import compile_ircode

    generator = GenerateLLVM()

    ir_functions = compile_ircode(source)
    for ir_func in ir_functions:
        generator.generate_code(ir_func)

    return str(generator.module)

def main():
    import sys

    if len(sys.argv) != 2:
        raise SystemExit(1)

    source = open(sys.argv[1]).read()
    llvm_code = compile_llvm(source)
    print(llvm_code)

if __name__ == '__main__':
    main()






