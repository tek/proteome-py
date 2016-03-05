from functools import wraps

from tryp import List, env, _, F
from tryp.test import later

from integration._support.base import VimIntegrationSpec


def _unite(f):
    @wraps(f)
    def wrapper(self):
        self._debug = True
        def go(unite):
            self.vim.amend_optionl('rtp', [unite])
            self.vim.cmd('source {}/plugin/*.vim'.format(unite))
            self.vim.cmd('source {}/plugin/unite/*.vim'.format(unite))
            self.vim.cmd('source {}/syntax/*.vim'.format(unite))
            return f(self, unite)
        env['UNITE_DIR'] % go
    return wrapper


class UniteSpec(VimIntegrationSpec):

    @property
    def _plugins(self):
        return List('proteome.plugins.unite')

    @_unite
    def select_add(self, unite):
        self.vim.cmd('ProSelectAdd')
        target = ' {}'.format(self.name1)
        later(lambda: self.vim.buffer.content.head.should.contain(target))

    @_unite
    def activate(self, unite):
        def active_type(tpe):
            self.vim.pvar('active').map(_['tpe']).should.contain(tpe)
        self.vim.cmd('ProAdd tpe2/dep')
        later(F(active_type, self.tpe2))
        self.vim.cmd('Projects')
        self._wait(0.1)
        self.vim.cmd('call feedkeys("\\<tab>\\<esc>\\<cr>")')
        later(F(active_type, self.tpe1))

    @_unite
    def remove(self, unite):
        self.vim.cmd('ProAdd tpe2/dep')
        self.vim.cmd('Projects')
        self._wait(0.1)
        self.vim.cmd('call feedkeys("\\<tab>\\<esc>k\\<cr>")')
        later(lambda: self.vim.pvar('projects').map(len).should.contain(1))

__all__ = ('UniteSpec',)
