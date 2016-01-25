import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List

from integration._support.base import VimIntegrationSpec


class NavSpec(VimIntegrationSpec):

    @property
    def _plugins(self):
        return List('proteome.plugins.config')

    def navigate(self):
        self.vim.cmd('ProNext')
        self._pvar_becomes('root_name', self.name2)
        self.vim.cmd('ProTo 0')
        self._pvar_becomes('root_name', self.name1)
        self.vim.cmd('ProPrev')
        self._pvar_becomes('root_name', self.name2)

__all__ = ('NavSpec',)
