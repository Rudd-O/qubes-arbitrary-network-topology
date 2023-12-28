import unittest


from qubesarbitrarynetworktopology.conjoin import ConjoinTracker


class TestConjoiners(unittest.TestCase):
    def test_simple_diff(self) -> None:
        config = ConjoinTracker.from_vm_table({"a": "b\nc"})
        reality = ConjoinTracker()
        self.assertListEqual(
            config.diff(reality), [("+", "a", "b", True), ("+", "a", "c", True)]
        )

    def test_diff_must_undo(self) -> None:
        config = ConjoinTracker()
        reality = ConjoinTracker.from_vm_table({"a": "b\nc"})
        self.assertListEqual(
            config.diff(reality), [("-", "a", "b", True), ("-", "a", "c", True)]
        )

    def test_backends(self) -> None:
        c = ConjoinTracker.from_vm_table({"a": "b\nc"})
        self.assertListEqual(c.backends("b"), ["a"])
        self.assertListEqual(c.backends("c"), ["a"])
        self.assertListEqual(c.backends("d"), [])
        self.assertListEqual(c.frontends("a"), ["b", "c"])

    def test_disjoin_reconjoin(self) -> None:
        c = ConjoinTracker.from_vm_table({"a": "b\nc"})
        c.disjoin("a", "b")
        self.assertListEqual(c.frontends("a"), ["c"])
        c.conjoin("a", "b", "zzz", "1")
        self.assertListEqual(c.frontends("a"), ["c", "b"])

    def test_diff_limit_to_vm(self) -> None:
        config = ConjoinTracker()
        reality = ConjoinTracker.from_vm_table({"a": "b\nc"})
        self.assertListEqual(
            config.diff(reality, limit_to_vm="b"), [("-", "a", "b", True)]
        )

    def test_diff_different_configs(self) -> None:
        a = ConjoinTracker.from_vm_table({"a": "b\nc"})
        b = ConjoinTracker.from_vm_table({"a": "b\nc someconfig"})
        self.assertListEqual(
            a.diff(b), [("-", "a", "c", True), ("+", "a", "c", "someconfig")]
        )
