from flexmock import flexmock  # type: ignore

import tek  # type: ignore

import tryp
from tryp import may, Maybe
from tryp.logging import tryp_stdout_logging

from proteome.nvim import NvimFacade


class MockNvimFacade(NvimFacade):

    def __init__(self):
        self.vars = {}
        super(MockNvimFacade, self).__init__(None)

    @may
    def var(self, name: str) -> Maybe[str]:  # type: ignore
        v = self.vars.get(name)
        if v is None:
            self.log.error('variable not found: {}'.format(name))
        return v


class Spec(tek.Spec):

    def setup(self, *a, **kw):
        tryp.development = True
        tryp_stdout_logging()
        super(Spec, self).setup(*a, **kw)


class MockNvimSpec(Spec):

    def setup(self, *a, **kw):
        super(MockNvimSpec, self).setup(*a, **kw)
        self.vim = MockNvimFacade()
        self.vim_mock = flexmock(self.vim)

__all__ = ['Spec']
