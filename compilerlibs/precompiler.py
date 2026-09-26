def init(logs, opcode_table):
    globals()["logs"] = logs
    globals()["opcode_table"] = opcode_table

class MixerClass():
    def _rotl(self, x, k):
        return ((x << k) & 0xFFFFFFFF) | (x >> (32 - k))

    def _pht(self, a, b):
        a &= 0xFFFFFFFF
        b &= 0xFFFFFFFF
        x = (a + b) & 0xFFFFFFFF
        y = (a + 2 * b) & 0xFFFFFFFF
        return x, y

    def _stage(self, state):
        a = state & 0xFFFFFFFF
        b = (state >> 32) & 0xFFFFFFFF
        a, b = self._pht(a, b)
        a ^= self._rotl(b, 11)
        b ^= self._rotl(a, 19)
        a, b = self._pht(a, b)
        a ^= a >> 13
        b ^= b >> 17
        a = (a * 0x9E3779B1) & 0xFFFFFFFF
        b = (b * 0x85EBCA77) & 0xFFFFFFFF
        a, b = self._pht(a, b)
        self.state = ((a << 32) | b) & 0xFFFFFFFFFFFFFFFF

    def _shuffle_opcodes(self):
        rslt = list(range(512))
        state = self.state & 0xFFFFFFFFFFFFFFFF
        for i in range(len(rslt)-1, 0, -1):
            state ^= ((state << 13) & 0xFFFFFFFFFFFFFFFF)
            state ^= state >> 7
            state ^= (state << 17) & 0xFFFFFFFFFFFFFFFF
            j = state % (i + 1)
            rslt[i], rslt[j] = rslt[j], rslt[i]
        self.opcodes = rslt

class PreCompiler(MixerClass):
    def __init__(self):
        self.IP = 0
        self.state = 1
        self.opcodes = [i for i in range(512)]
        self.line = 1

    def _write_operand(self, address, parsed):
        type_, value = parsed["type"], parsed["value"]
        if type_ == "register":
            return 6
        elif type_ == "number":
            if value <= (2**8-1):
                return 10
            elif value <= (2**32-1):
                return 34
            elif value <= (2**64-1):
                return 66
    def parse_register(self, operand):
        if not operand.startswith("r"):
            logs.fatal(f"Not a register: {operand} at line {self.line}.")
            exit(-1)

        if operand == "rip":
            return 15

        if not operand[1:].isdigit():
            logs.fatal(f"Not a register: {operand} at line {self.line}.")
            exit(-1)

        if not 0 <= int(operand[1:]) <= 15:
            logs.fatal(f"Invalid register {operand} at line {self.line}.")
            exit(-1)

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

    def parse(self, lines):
        self.line = 1
        self.instruction = 0
        lines_len = {}
        result = {}

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
                if len(args) != 1:
                    logs.fatal(f"RET expects 1 operand at line {self.line}.")
                    exit(-1)

                opcode_num = self.opcodes.index(opcode_table[opcode])
                length += 9
                length += self._write_operand(self.IP + 9, self.parse_operand(args[0]));


                result |= {self.instruction: (self.state, length, self.IP)}

                self.IP += length
                lines_len |= {self.line: length}
                continue
            elif opcode == "jmp":
                length += 107
                logical_opcode = opcode_table[opcode]
                opcode_num = self.opcodes.index(logical_opcode)

            elif opcode in ["add", "mov", "sub"]:
                if len(args) != 2:
                    logs.fatal(f"{opcode.upper()} expects 2 operands at line {self.line}.")
                    exit(-1)

                logical_opcode = opcode_table[opcode]
                opcode_num = self.opcodes.index(logical_opcode)

                if self.parse_register(args[0]) == 15:
                    logs.warning("Trying to change RIP can cause unexcepted behaviour, i recommend use jmp, but if u need relative jumps its ok.")

                length += 13
                length += self._write_operand(self.IP + 13, self.parse_operand(args[1]));

            else:
                logs.fatal(f"Invalid instruction {opcode} at line {self.line}.")
                exit(-1)

            result |= {self.instruction: (self.state, length, self.IP)}

            self._stage(self.IP ^ self.state ^ opcode_num ^ logical_opcode)
            self._shuffle_opcodes()

            self.IP += length

        return result