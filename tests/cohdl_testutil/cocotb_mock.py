from __future__ import annotations


import random
from .cocotb_util import ConstraindValue, SequentialTest, step


#
# test code
#


class ValuePair:
    def __init__(self, dutValue, mockValue: ConstraindValue, name: str | None = None):
        self.dutValue = dutValue
        self.mockValue = mockValue
        self.name = name
        self.is_set = False
        self.history = []

    def record(self):
        self.history.append((str(self.mockValue), str(self.dutValue)))

    def get(self):
        return self.mockValue.value

    def randomize(self):
        self.mockValue.randomize()
        self.assign(self.mockValue)

    def assign(self, val: ConstraindValue):
        if isinstance(val, ValuePair):
            val = val.mockValue

        self.mockValue.assign(val)
        self.dutValue.value = self.mockValue.value
        self.is_set = True

    def assign_maybe(self, val, likelyhook):
        if random.random() < likelyhook:
            self.assign(val)

    def __ilshift__(self, value):
        self.assign(value)
        return self

    def __or__(self, other):
        if isinstance(other, ValuePair):
            other = other.mockValue

        return self.mockValue | other

    def __and__(self, other):
        if isinstance(other, ValuePair):
            other = other.mockValue

        return self.mockValue & other

    def __xor__(self, other):
        if isinstance(other, ValuePair):
            other = other.mockValue

        return self.mockValue ^ other

    def __bool__(self):
        return bool(self.mockValue)


class OutPair(ValuePair):
    def assign(self, val: ConstraindValue | None):
        if val is None:
            self.is_set = False
        else:
            if isinstance(val, ValuePair):
                val = val.mockValue
            self.mockValue.assign(val)
            self.is_set = True

    def reset(self):
        self.mockValue.reset()


class MockBase:
    def __init__(self, clk, *, reset_cond=lambda: False, record=False, no_assert=False):
        self._seq = SequentialTest(clk)

        self._running_mock_sim = self._mock_simulation()
        self._reset_cond = reset_cond

        self._pairs: list[ValuePair] = []
        self._record = record
        self._no_assert = no_assert

    def _mock_simulation(self):
        yield
        while True:
            yield from self.mock()
            yield

    def record(self):
        for pair in self._pairs:
            pair.record()

    def _reset(self):
        for pair in self._pairs:
            if isinstance(pair, OutPair):
                pair.reset()

    def dump_record(self):
        print("".join(f"{pair.name:>11}" for pair in self._pairs))
        print()
        for records in zip(*[pair.history for pair in self._pairs]):
            print("".join([f"({record[0]:>5} {record[1]:>5}) " for record in records]))

    def zero_pairs(self):
        for pair in self._pairs:
            pair.assign(0)

    def zero_inputs(self):
        for pair in self._pairs:
            if not isinstance(pair, OutPair):
                pair.assign(0)

    def check(self):
        try:
            for pair in self._pairs:
                if not isinstance(pair, OutPair):
                    continue

                if pair.is_set and not self._no_assert:
                    if pair.name is None:
                        assert (
                            pair.dutValue == pair.mockValue.value
                        ), f"{pair.dutValue.value} != {pair.mockValue}"
                    else:
                        assert (
                            pair.dutValue == pair.mockValue.value
                        ), f"{pair.dutValue.value} != {pair.mockValue} ({pair.name})"
        except BaseException as e:
            print(f"error on {pair.name}")
            self.dump_record()
            raise e

    def inpair(self, dutValue, mockValue, name: str | None = None):
        new = ValuePair(dutValue, mockValue, name)
        self._pairs.append(new)
        return new

    def outpair(self, dutValue, mockValue, name: str | None = None):
        new = OutPair(dutValue, mockValue, name)
        self._pairs.append(new)
        return new

    async def tick(self):
        await step()
        await self._seq.tick()
        await step()

    def reset_sim(self):
        self._reset()
        self._running_mock_sim = self._mock_simulation()
        next(self._running_mock_sim)

    async def delta_step(self):
        self.concurrent()
        await self._seq.delta()
        # record states
        if self._record:
            self.record()
        self.check()

    async def next_step(self):
        self.concurrent()

        if self._reset_cond():
            self.reset_sim()
        else:
            # run mock simulation
            next(self._running_mock_sim)

        self.concurrent()

        # run cocotb sim
        await self._seq.tick()

        # record states
        if self._record:
            self.record()
        self.check()

    def await_cond(self, cond):
        yield
        while not cond():
            yield

    def concurrent(self):
        pass

    def mock(self):
        yield
