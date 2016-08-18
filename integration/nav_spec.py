import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List

from integration._support.base import ProteomePluginIntegrationSpec


class NavSpec(ProteomePluginIntegrationSpec):

    @property
    def _plugins(self):
        return List('proteome.plugins.config')

    def navigate(self):
        self.vim.cmd('ProNext')
        self._project_becomes(self.name2)
        self.vim.cmd('ProTo 0')
        self._project_becomes(self.name1)
        self.vim.cmd('ProPrev')
        self._project_becomes(self.name2)

__all__ = ('NavSpec',)
