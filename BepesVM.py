from _monstermem import *

mem = MonsterMem()
mem.allocate(8192)

class BepesVM:
    def __init__(self, memory, additional_memory):
        self.memory = memory
        self.opcodes = [i for i in range(512)]
        self.state = 1
        self.registers = [0,0,0,0,0,0,0,0,
                          0,0,0,0,0,0,0,0]
        self.flags = 0
        self.additional_memory = additional_memory
        self.call_stack = []

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

    def _get_operand_value(self, operand_address):
        if self.memory.read(operand_address, 1):
            return self.memory.read(operand_address + 1, 64), 65
        else:
            return self.registers[self.memory.read(operand_address + 1, 4)], 5


    def run(self, code):
        self.registers[15] = code

        while True:
            IP = self.registers[15]

            length = 0
            opcode = self.memory.read(IP, 9)

            if self.opcodes[opcode] == 4:
                value, lng = self._get_operand_value(IP + 9)
                return value
            elif self.opcodes[opcode] in [0, 255, 137]:
                register = self.memory.read(IP + 9, 4)
                value, lng = self._get_operand_value(IP + 13)
                if self.opcodes[opcode] == 255:
                    value = self.registers[register] + value
                elif self.opcodes[opcode] == 137:
                    value = self.registers[register] - value
                self.registers[register] = value
                length = 13 + lng
            elif self.opcodes[opcode] == 29:
                target_is_register = self.memory.read(IP + 9, 1)

                if not target_is_register:
                    negative = self.memory.read(IP + 10, 1)
                    magnitude = self.memory.read(IP + 11, 31)

                    offset = -magnitude if negative else magnitude
                    target_ip = IP + offset
                else:
                    target_register = self.memory.read(IP + 10, 32)
                    target_ip = self.registers[target_register]
                state_is_register = self.memory.read(IP + 42, 1)
                if not state_is_register:
                    target_state = self.memory.read(IP + 43, 64)
                else:
                    state_register = self.memory.read(IP + 43, 64)
                    target_state = self.registers[state_register]
                self.state = target_state & 0xFFFFFFFFFFFFFFFF
                self.registers[15] = target_ip

                self._shuffle_opcodes()
                continue

            self._stage(IP ^ self.state ^ self.opcodes[opcode] ^ opcode)
            self._shuffle_opcodes()
            self.registers[15] += length


byt = b'\x7f\x84\x00\x00\x00\x00\x00\x00\x14\xe4f\x10\x00\x00\x00\x00\x00\x00\x00\x1a\xb0\x00\x00\x01\xe4\xc6\x85\x9c\xf6\xd1\x85\xb5\x8bO\x01\xf8`\x00\x00\x00\x00\x00\x00\x0fm\x84\x00\x00\x02\xe1\x8d\x0b9\xed\xa3\x0bk\x14'
for i,j in enumerate(byt):
    mem.write(i*8, 8, j)

a = BepesVM(mem,{})
b = a.run(0)

print(b)

# compile