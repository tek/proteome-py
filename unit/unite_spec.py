from proteome.plugins.unite import UniteSelectAdd

from unit._support.spec import UnitSpec


class UniteSpec(UnitSpec):

    def setup(self):
        super().setup()

    def test(self):
        m = UniteSelectAdd('a', 'b')

__all__ = ('UniteSpec',)
