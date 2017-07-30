from amino import __
from amino.test.spec_spec import later

from integration._support.base import ProteomePluginIntegrationSpec


class CloneSpec(ProteomePluginIntegrationSpec):

    def valid(self):
        name = 'proteome.nvim'
        self.vim.cmd('ProClone tek/{}'.format(name))
        readme = self.base / self.tpe1 / name / 'README.md'
        later(lambda: readme.exists().should.be.ok)
        self._pvar_becomes_map('active', name, __['name'])

    def invalid(self):
        name = 'invalid@#'
        self.vim.cmd('ProClone tek/{}'.format(name))
        self._log_line(-1, __.startswith('failed to clone'))

__all__ = ('CloneSpec',)
