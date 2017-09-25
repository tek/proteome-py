from amino import List, __
from amino.test import temp_dir

from kallikrein import Expectation, k, kf, unsafe_kf
from kallikrein.matchers.either import be_right

from ribosome.test.unite import unite
from ribosome.test.integration.klk import later

from integration._support.base import DefaultSpec


class UniteSpec(DefaultSpec):
    '''unite menus
    candidates for addable projects $addable_candidates
    contents of the `ProSelectAdd` menu $select_add
    contents of the `ProSelectAddAll` menu $select_add_all
    add multiple projects $selectable_add
    activate a project $activate
    delete a project $delete
    delete a project with the mapping `d` $delete_by_mapping
    delete multiple projects by selecting $selectable_delete
    '''

    @property
    def components(self) -> List[str]:
        return List('unite')

    def _mk_projects(self) -> None:
        self.other = 'other'
        self.other2 = 'other2'
        temp_dir(str(self.type1_base / self.other))
        temp_dir(str(self.base2 / self.tpe1 / self.other2))

    def _count(self, num: int) -> Expectation:
        return later(kf(lambda: self.vim.vars.p('projects') / len).must(be_right(num)))

    @unite
    def addable_candidates(self) -> Expectation:
        self._mk_projects()
        result = self.vim.call('_proteome_unite_addable')
        target = List(dict(word=self.name1), dict(word=self.other2))
        return k(result).must(be_right(target))

    @unite
    def select_add(self) -> Expectation:
        self._mk_projects()
        self.cmd_sync('ProSelectAdd')
        lines = List(
            f' {self.name1}',
            f' {self.other2}',
        )
        return self._buffer_content(lines)

    @unite
    def select_add_all(self) -> Expectation:
        self._mk_projects()
        self.cmd_sync('ProSelectAddAll -auto-resize')
        lines = List(
            ' {}/{}'.format(self.tpe1, self.name1),
            ' {}/{}'.format(self.tpe2, self.name2),
            ' {}/{}'.format(self.tpe1, self.other2),
            ' {}/{}'.format(self.typed1, self.other),
            ' {}'.format(self.name1),
            ' {}'.format(self.other2),
        )
        return self._buffer_content(lines)

    @unite
    def selectable_add(self) -> Expectation:
        self._mk_projects()
        self.cmd_sync('ProSelectAddAll -auto-resize')
        self.cmd_sync('call feedkeys("\\<space>\\<space>\\<space>\\<cr>")')
        return self._count(3)

    @unite
    def activate(self) -> Expectation:
        def active_type(tpe: str) -> Expectation:
            return kf(lambda: self.vim.vars.p('active').map(__['tpe'])).must(be_right(tpe))
        self.cmd_sync('ProAdd tpe2/dep')
        later(active_type(self.tpe2))
        self.cmd_sync('Projects')
        self.cmd_sync('call feedkeys("\\<tab>\\<esc>\\<cr>")')
        return later(active_type(self.tpe1))

    @unite
    def delete(self) -> Expectation:
        self.cmd_sync('ProAdd! tpe2/dep')
        self._count(2)
        self.cmd_sync('Projects')
        self.cmd_sync('call feedkeys("\\<tab>\\<esc>k\\<cr>")')
        return self._count(1)

    @unite
    def delete_by_mapping(self) -> Expectation:
        self.cmd_sync('ProAdd! tpe2/dep')
        self._count(2)
        self.cmd_sync('Projects')
        self.vim.feedkeys('d')
        return self._count(1)

    @unite
    def selectable_delete(self) -> Expectation:
        ''' Remove two projects
        by selecting them via `<space>` and pressing `d`
        '''
        self.cmd_sync('ProAdd! tpe2/dep')
        self._count(2)
        self.cmd_sync('Projects')
        self.cmd_sync('call feedkeys("\\<space>\\<space>d")')
        return self._count(0)

__all__ = ('UniteSpec',)
