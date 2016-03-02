import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp.test import later

from integration._support.base import VimIntegrationSpec


class CloneSpec(VimIntegrationSpec):

    def clone(self):
        self._debug = True
        name = 'proteome.nvim'
        self.vim.cmd('ProClone tek/{}'.format(name))
        readme = self.base / self.tpe1 / name / 'README.md'
        later(lambda: readme.exists().should.be.ok)

__all__ = ('CloneSpec',)
