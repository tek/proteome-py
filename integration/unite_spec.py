from functools import wraps

from tryp import List, env, _, F
from tryp.test import later, temp_dir

from integration._support.base import VimIntegrationSpec


def _unite(f):
    @wraps(f)
    def wrapper(self):
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

    def _mk_projects(self):
        self.other = 'other'
        self.other2 = 'other2'
        temp_dir(str(self.type1_base / self.other))
        temp_dir(str(self.base2 / self.tpe1 / self.other2))

    @_unite
    def select_add(self, unite):
        self._mk_projects()
        self.vim.cmd('ProSelectAdd')
        lines = List(
            ' {}'.format(self.name1),
            ' {}'.format(self.other2),
        )
        later(lambda: self.vim.buffer.content.should.equal(lines))

    @_unite
    def select_add_all(self, unite):
        self._mk_projects()
        self.vim.cmd('ProSelectAddAll -auto-resize')
        lines = List(
            ' {}/{}'.format(self.tpe1, self.name1),
            ' {}/{}'.format(self.tpe2, self.name2),
            ' {}/{}'.format(self.tpe1, self.other2),
            ' {}/{}'.format(self.typed1, self.other),
            ' {}'.format(self.name1),
            ' {}'.format(self.other2),
        )
        later(lambda: self.vim.buffer.content.should.equal(lines))

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
    def delete(self, unite):
        def count(num):
            return (self.vim.pvar('projects') / len).should.contain(num)
        self.vim.cmd('ProAdd tpe2/dep')
        later(F(count, 2))
        self.vim.cmd('Projects')
        self._wait(0.1)
        self.vim.cmd('call feedkeys("\\<tab>\\<esc>k\\<cr>")')
        later(F(count, 1))

    @_unite
    def delete_by_mapping(self, unite):
        def count(num):
            return (self.vim.pvar('projects') / len).should.contain(num)
        self.vim.cmd('ProAdd tpe2/dep')
        later(F(count, 2))
        self.vim.cmd('Projects')
        self._wait(0.1)
        self.vim.feedkeys('d')
        later(F(count, 1))

__all__ = ('UniteSpec',)
