import argparse
from _monstermem import *
from katzo import logger
from compilerlibs.precompiler import *
import pathlib

logs = logger.Logger()

opcode_table = {
    "ret": 4,
    "mov": 0,
    "add": 255,
    "sub": 137,
    "jmp": 29
}
init(logs, opcode_table)

class BepesVMCompiler(MixerClass):
    def __init__(self, file):
        self.IP = 0
        self.temp_mem = MonsterMem()
        self.state = 1
        self.opcodes = [i for i in range(512)]
        self.file = file
        self.line = 1

    def _write_operand(self, address, parsed):
        type_, value = parsed["type"], parsed["value"]
        if type_ == "register":
            self.temp_mem.allocate(5)
            self.temp_mem.write(address, 5, (value & 0xF))
            return 5
        elif type_ == "number":
            self.temp_mem.allocate(65)
            self.temp_mem.write(address, 65, (1 << 64) | (value & 0xFFFFFFFFFFFFFFFF))
            return 65

    def parse_register(self, operand):
        if operand == "rip":
            return 15

        return int(operand[1:])

    def parse_operand(self, operand):
        if operand.startswith("r"):
            return {"type": "register", "value": self.parse_register(operand)}
        elif operand.startswith("0x"):
            return {"type": "number", "value": int(operand[2:], 16)}
        elif operand.startswith("0b"):
            return {"type": "number", "value": int(operand[2:], 2)}
        elif operand.startswith("0o"):
            return {"type": "number", "value": int(operand[2:], 8)}
        else:
            return {"type": "number", "value": int(operand)}

    def compile(self):
        file = open(self.file, "r")

        lines = file.readlines()

        adv_compiler = PreCompiler()
        table = adv_compiler.parse(lines.copy())

        self.instruction = 0
        self.line = 1
        lines_len = {}

        for self.line, i in enumerate(lines, 1):

            i = i.split(";", 1)[0].strip()
            if not i:
                continue

            self.instruction += 1

            opcode, args = i.split(maxsplit=1)
            opcode = opcode.lower()
            args = [x.strip().lower() for x in args.split(",")]

            length = 0
            opcode_num = None
            logical_opcode = 0

            if opcode == "ret":
                opcode_num = self.opcodes.index(opcode_table[opcode])
                self.temp_mem.allocate(9)
                self.temp_mem.write(self.IP, 9, opcode_num)
                length += 9
                length += self._write_operand(self.IP + 9, self.parse_operand(args[0]));
                self.IP += length

                continue
            elif opcode == "jmp":
                logical_opcode = opcode_table[opcode]
                opcode_num = self.opcodes.index(logical_opcode)

                is_reg = False

                if args[0][0] in "+-":
                    val = self.parse_operand(args[0][1:])["value"]
                    match args[0][0]:
                        case "+":
                            instr = self.instruction + val
                        case "-":
                            instr = self.instruction - val

                    target_addr = (table[instr][2] - table[self.instruction][2])  # IP
                    state = table[instr][0]
                else:
                    if self.parse_operand(args[0])["type"] == "register":
                        is_reg = True
                    else:
                        # target = args[0]
                        val = self.parse_operand(args[0])["value"]
                        target_addr = (table[val][2] - table[self.instruction][2]) # IP
                        state = table[val][0]

                self.temp_mem.allocate(107)

                self.temp_mem.write(self.IP, 9, opcode_num)

                if is_reg:
                    encoded_offset = (1 << 32) | (self.parse_operand(args[0])["value"])
                    if self.parse_operand(args[1])["type"] == "register":
                        state = (1 << 64) | (self.parse_operand(args[1])["value"])
                    else:
                        state = (self.parse_operand(args[1])["value"])
                else:
                    encoded_offset = (
                                         (1 << 31) if target_addr < 0 else 0
                                     ) | abs(target_addr)

                self.temp_mem.write(self.IP + 9, 33, encoded_offset)
                self.temp_mem.write(self.IP + 42, 65, state)

                length += 107

            elif opcode in ["add", "mov", "sub"]:
                logical_opcode = opcode_table[opcode]

                opcode_num = self.opcodes.index(logical_opcode)
                self.temp_mem.allocate(13)
                self.temp_mem.write(self.IP, 9, opcode_num)

                self.temp_mem.write(self.IP + 9, 4, self.parse_register(args[0]))
                length += 13
                length += self._write_operand(self.IP + 13, self.parse_operand(args[1]));


            self._stage(self.IP ^ self.state ^ opcode_num ^ logical_opcode)
            self._shuffle_opcodes()

            lines_len |= {self.line: length}

            self.IP += length

parser = argparse.ArgumentParser()
parser.add_argument("filename")
parser.add_argument("-o", "--out", default=None)
args = parser.parse_args()

print("BepASM Compiler")
compiler = BepesVMCompiler(args.filename)
compiler.compile()

out = args.out
if out is None:
    out = pathlib.Path(args.filename).stem + ".bvm"
open(out, "wb").write(compiler.temp_mem.memory)

