class MonsterMem:
    def __init__(self):
        self.memory = bytearray()
        self.current_bit = 0

    def _get_mask(self, bitlen):
        return (1 << bitlen) - 1

    def _get_int_from_num(self, bytes_):  # BE!
        return int.from_bytes(bytes_, "big")

    def read(self, from_bit, length):
        if from_bit < 0 or length < 0:
            raise ValueError("negative address/length")

        if from_bit + length > len(self.memory) * 8:
            raise IndexError("reading outside allocated memory")

        bytes_ = self.memory[from_bit // 8:(from_bit + length + 7) // 8]
        mask = self._get_mask(length)

        need_to_rshift = (8 - (from_bit + length) % 8) % 8

        return (self._get_int_from_num(bytes_) >> need_to_rshift) & mask

    def allocate(self, bitlen):
        if bitlen < 0:
            raise ValueError("negative bitlen")

        address = self.current_bit
        end_bit = self.current_bit + bitlen

        need_bytes = (end_bit + 7) // 8

        if need_bytes > len(self.memory):
            self.memory += bytearray([0]) * (need_bytes - len(self.memory))

        self.current_bit = end_bit

        return address

    def write(self, address, bitlen, value):
        if address < 0 or bitlen <= 0:
            raise ValueError("negative (or length=0) address/length")

        if address >= (len(self.memory) * 8):
            raise ValueError("address out of range")

        if (address + bitlen) > (len(self.memory) * 8):
            raise ValueError("bitlen out of range")

        if value >= (1 << bitlen):
            raise OverflowError(
                f"{value} doesn't fit into {bitlen} bits"
            )

        for i in range(bitlen):
            pos = address + i

            byte_pos = pos // 8
            bit_pos = 7 - (pos % 8)

            bit_value = (value >> (bitlen - 1 - i)) & 1

            if bit_value:
                self.memory[byte_pos] |= 1 << bit_pos
            else:
                self.memory[byte_pos] &= ~(1 << bit_pos)


class MonsterMemData:
    def __init__(self, mm, address, leng):
        self.mm = mm
        self.address = address
        self.length = leng

    def __eq__(self, othermmd):
        return (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd) == self.get()

    def __and__(self, othermmd):
        return (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd) & self.get()

    def __or__(self, othermmd):
        return (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd) | self.get()

    def __xor__(self, othermmd):
        return (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd) ^ self.get()

    def __lshift__(self, othermmd):
        return self.get() << (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd)

    def __rshift__(self, othermmd):
        return self.get() >> (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd)

    def __add__(self, othermmd):
        return (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd) + self.get()

    def __sub__(self, othermmd):
        return self.get() - (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd)

    def __mul__(self, othermmd):
        return (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd) * self.get()

    def __mod__(self, othermmd):
        return self.get() % (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd)

    def __pow__(self, othermmd):
        return self.get() ** (othermmd.get() if isinstance(othermmd, self.__class__) else othermmd)

    def get(self):
        return self.mm.read(self.address, self.length)

    def set(self, data):
        self.mm.write(self.address, self.length, data)

