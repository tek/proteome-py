import sure  # NOQA
from flexmock import flexmock  # NOQA

from fn import _

from tryp.test import later
from tryp import __

from integration._support.base import VimIntegrationSpec


class CloneSpec(VimIntegrationSpec):

    def valid(self):
        name = 'proteome.nvim'
        self.vim.cmd('ProClone tek/{}'.format(name))
        readme = self.base / self.tpe1 / name / 'README.md'
        later(lambda: readme.exists().should.be.ok)
        self._pvar_becomes_map('active', name, _['name'])

    def invalid(self):
        name = 'invalid@#'
        self.vim.cmd('ProClone tek/{}'.format(name))
        self._log_line(-1, __.startswith('failed to clone'))

__all__ = ('CloneSpec',)
