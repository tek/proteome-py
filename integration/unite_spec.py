from functools import wraps
from typing import Callable, Any

from amino import List, env, __
from amino.test import temp_dir

from ribosome.test.integration.spec_spec import later

from integration._support.base import ProteomePluginIntegrationSpec


def _unite(f: Callable[[Any, str], None]) -> Callable[[Any], None]:
    @wraps(f)
    def wrapper(self: Any) -> None:
        def go(unite: str) -> Any:
            self.vim.options.amend_l('rtp', [unite])
            self.vim.cmd('source {}/plugin/*.vim'.format(unite))
            self.vim.cmd('source {}/plugin/unite/*.vim'.format(unite))
            self.vim.cmd('source {}/syntax/*.vim'.format(unite))
            return f(self, unite)
        env['UNITE_DIR'] % go
    return wrapper


class UniteSpec(ProteomePluginIntegrationSpec):

    @property
    def _plugins(self) -> List[str]:
        return List('proteome.plugins.unite')

    def _mk_projects(self) -> None:
        self.other = 'other'
        self.other2 = 'other2'
        temp_dir(str(self.type1_base / self.other))
        temp_dir(str(self.base2 / self.tpe1 / self.other2))

    def _count(self, num: int) -> bool:
        return later(lambda: (self.vim.vars.p('projects') / len).should.contain(num))

    @_unite
    def select_add(self, unite: str) -> None:
        self._mk_projects()
        self.vim.cmd('ProSelectAdd')
        lines = List(
            ' {}'.format(self.name1),
            ' {}'.format(self.other2),
        )
        later(lambda: self.vim.buffer.content.should.equal(lines))

    @_unite
    def select_add_all(self, unite: str) -> None:
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
    def selectable_add(self, unite: str) -> None:
        self._mk_projects()
        self.vim.cmd('ProSelectAddAll -auto-resize')
        self._wait(0.1)
        self.vim.cmd('call feedkeys("\\<space>\\<space>\\<space>\\<cr>")')
        self._count(3)

    @_unite
    def activate(self, unite: str) -> None:
        def active_type(tpe: str) -> None:
            self.vim.vars.p('active').map(__['tpe']).should.contain(tpe)
        self.vim.cmd('ProAdd tpe2/dep')
        later(active_type, self.tpe2)
        self.vim.cmd('Projects')
        self._wait(0.1)
        self.vim.cmd('call feedkeys("\\<tab>\\<esc>\\<cr>")')
        later(active_type, self.tpe1)

    @_unite
    def delete(self, unite: str) -> None:
        self.vim.cmd('ProAdd tpe2/dep')
        self._count(2)
        self.vim.cmd('Projects')
        self._wait(0.1)
        self.vim.cmd('call feedkeys("\\<tab>\\<esc>k\\<cr>")')
        self._count(1)

    @_unite
    def delete_by_mapping(self, unite: str) -> None:
        self.vim.cmd('ProAdd tpe2/dep')
        self._count(2)
        self.vim.cmd('Projects')
        self._wait(0.1)
        self.vim.feedkeys('d')
        self._count(1)

    @_unite
    def selectable_delete(self, unite: str) -> None:
        ''' Remove two projects
        by selecting them via `<space>` and pressing `d`
        '''
        self.vim.cmd('ProAdd tpe2/dep')
        self._count(2)
        self.vim.cmd('Projects')
        self._wait(0.1)
        self.vim.cmd('call feedkeys("\\<space>\\<space>d")')
        self._count(0)

__all__ = ('UniteSpec',)
