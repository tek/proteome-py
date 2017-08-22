from ribosome.test.spec import MockNvimSpec

from proteome.test import Spec


class UnitSpec(MockNvimSpec, Spec):

    def __init__(self) -> None:
        MockNvimSpec.__init__(self, 'proteome')

    def setup(self) -> None:
        MockNvimSpec.setup(self)
        Spec.setup(self)

__all__ = ('UnitSpec',)
