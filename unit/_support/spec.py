from ribosome.test.spec import MockNvimSpec

from proteome.test import Spec


class UnitSpec(MockNvimSpec, Spec):

    def __init__(self) -> None:
        super().__init__('proteome')

    def setup(self) -> None:
        MockNvimSpec.setup(self)
        Spec.setup(self)

__all__ = ('UnitSpec',)
