import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List, env
from tryp.test import later

from integration._support.base import VimIntegrationSpec


class UniteSpec(VimIntegrationSpec):

    @property
    def _plugins(self):
        return List('proteome.plugins.unite')

    def unite(self):
        self._debug = True
        def go(unite):
            self.vim.amend_optionl('rtp', [unite])
            self.vim.cmd('source {}/plugin/*.vim'.format(unite))
            self.vim.cmd('source {}/plugin/unite/*.vim'.format(unite))
            self.vim.cmd('source {}/syntax/*.vim'.format(unite))
            self.vim.cmd('ProSelectAdd')
            target = ' {}'.format(self.name1)
            later(lambda: self.vim.buffer.content.head.should.contain(target))
        env['UNITE_DIR'] % go

__all__ = ('UniteSpec',)
