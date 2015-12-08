from flexmock import flexmock  # type: ignore

import tek  # type: ignore

from tryp import may, Maybe

import trypnv
from trypnv import Log

from proteome.nvim import NvimFacade


class MockNvimFacade(NvimFacade):

    def __init__(self):
        self.vars = {}
        super(MockNvimFacade, self).__init__(None)

    @may
    def var(self, name) -> Maybe[str]:
        v = self.vars.get(name)
        if v is None:
            Log.error('variable not found: {}'.format(name))
        return v


class Spec(tek.Spec):

    def setup(self, *a, **kw):
        trypnv.development = True
        super(Spec, self).setup(*a, **kw)


class MockNvimSpec(Spec):

    def setup(self, *a, **kw):
        super(MockNvimSpec, self).setup(*a, **kw)
        self.vim = MockNvimFacade()
        self.vim_mock = flexmock(self.vim)

__all__ = ['Spec']
