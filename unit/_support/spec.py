import proteome.test

from ribosome.test.spec import MockNvimSpec


class UnitSpec(MockNvimSpec, proteome.test.Spec):

    def __init__(self):
        super().__init__('proteome')

    def setup(self):
        super().setup()

__all__ = ('UnitSpec',)
