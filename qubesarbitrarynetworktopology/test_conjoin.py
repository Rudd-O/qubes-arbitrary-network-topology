import unittest


from qubesarbitrarynetworktopology.conjoin import ConjoinTracker, Parameters


class TestConjoiners(unittest.TestCase):
    def test_simple_diff(self) -> None:
        config = ConjoinTracker.from_vm_table({"a": "b\nc"})
        reality = ConjoinTracker()
        self.assertListEqual(
            config.diff(reality),
            [("+", "a", "b", Parameters()), ("+", "a", "c", Parameters())],
        )

    def test_diff_must_undo(self) -> None:
        config = ConjoinTracker()
        reality = ConjoinTracker.from_vm_table({"a": "b\nc"})
        self.assertListEqual(
            config.diff(reality),
            [("-", "a", "b", Parameters()), ("-", "a", "c", Parameters())],
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
        c.conjoin(
            "a", "b", Parameters.from_string("frontend_mac=12:12:12:12:12:12"), "1"
        )
        self.assertListEqual(c.frontends("a"), ["c", "b"])

    def test_change_mac(self) -> None:
        a = ConjoinTracker.from_vm_table({"a": "b frontend_mac=ab:ab:ab:ab:ab:ab\nc"})
        b = ConjoinTracker.from_vm_table({"a": "b frontend_mac=ab:ab:ab:ab:ab:cd\nc"})
        self.assertListEqual(
            b.diff(a),
            [
                (
                    "-",
                    "a",
                    "b",
                    Parameters.from_string("frontend_mac=ab:ab:ab:ab:ab:ab"),
                ),
                (
                    "+",
                    "a",
                    "b",
                    Parameters.from_string("frontend_mac=ab:ab:ab:ab:ab:cd"),
                ),
            ],
        )

    def test_diff_limit_to_vm(self) -> None:
        config = ConjoinTracker()
        reality = ConjoinTracker.from_vm_table({"a": "b\nc"})
        self.assertListEqual(
            config.diff(reality, limit_to_vm="b"), [("-", "a", "b", Parameters())]
        )

    def test_diff_different_configs(self) -> None:
        a = ConjoinTracker.from_vm_table({"a": "b\nc"})
        b = ConjoinTracker.from_vm_table({"a": "b\nc frontend_mac=12:12:12:12:12:12"})
        self.assertListEqual(
            b.diff(a),
            [
                (
                    "-",
                    "a",
                    "c",
                    Parameters(),
                ),
                (
                    "+",
                    "a",
                    "c",
                    Parameters.from_string("frontend_mac=12:12:12:12:12:12"),
                ),
            ],
        )

    def test_bad_config_raises_valueerror(self) -> None:
        self.assertRaises(
            ValueError, lambda: Parameters.from_string("frontend_mac=12:12:12:12:12")
        )
