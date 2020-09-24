# Pulse compiler (uses clang)

import subprocess
import sys
import os.path
import tempfile

from llvm import compile_llvm
from error import errors_reported

_rtlib = os.path.join(os.path.dirname(__file__), 'pulsert.c')

# clang installation
CLANG = 'clang'

def main():
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: pulsec filename\n")
        raise SystemExit(1)

    try:
        f = open(sys.argv[1])
    except:
        sys.stderr.write("Error: file '{}' does not exist\n".format(sys.argv[1]))
        raise SystemExit(1)
        
    source = f.read()
    llvm_code = compile_llvm(source)

    # out = os.path.join(os.path.dirname(sys.argv[1]), os.path.splitext(os.path.basename(sys.argv[1]))[0]);
    out = os.path.splitext(os.path.basename(sys.argv[1]))[0];
    if not errors_reported():
        with tempfile.NamedTemporaryFile(suffix='.ll') as f:
            f.write(llvm_code.encode('utf-8'))
            f.flush()
            subprocess.check_output([CLANG, '-DNEED_MAIN', f.name, '-o', out, _rtlib])

if __name__ == '__main__':
    main()
