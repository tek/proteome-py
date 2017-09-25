from typing import Optional

from amino import List, Map, Nothing

from ribosome.machine.transition import may_handle
from ribosome.machine.state import Component, ComponentMachine
from ribosome.unite import UniteSource
from ribosome.unite.data import UniteKind
from ribosome.machine.message_base import Message
from ribosome.machine.machine import Machine
from ribosome.nvim import NvimFacade, NvimIO

from proteome.components.unite.data import UniteSelectAdd, UniteSelectAddAll, UniteProjects, UniteMessage
from proteome.components.unite import UniteNames

addable = UniteSource(UniteNames.addable, UniteNames.addable_candidates, UniteNames.addable, Nothing)
all_addable = UniteSource(UniteNames.all_addable, UniteNames.all_addable_candidates, UniteNames.addable, Nothing)
add_action = Map(name='add', handler=UniteNames.add_project, desc='add project')
add_pro = UniteKind(UniteNames.addable, List(add_action))
projects = UniteSource(UniteNames.projects, UniteNames.projects_candidates, UniteNames.project, Nothing)
delete_action = Map(name='delete', handler=UniteNames.delete_project, desc='delete project')
activate_action = Map(name='activate', handler=UniteNames.activate_project, desc='activate project', is_selectable=0)
project = UniteKind(UniteNames.project, List(activate_action, delete_action))
entities = List(addable, all_addable, add_pro, projects, project)


class UniteTransitions(Component):

    def unite_cmd(self, cmd: str) -> None:
        args = ' '.join(self.msg.unite_args)
        self.vim.cmd('Unite {} {}'.format(cmd, args))

    @may_handle(UniteSelectAdd)
    def select_add(self) -> None:
        self.unite_cmd(UniteNames.addable)

    @may_handle(UniteSelectAddAll)
    def select_add_all(self) -> None:
        self.unite_cmd(UniteNames.all_addable)

    @may_handle(UniteProjects)
    def projects(self) -> None:
        self.unite_cmd(UniteNames.projects)


class Plugin(ComponentMachine):

    def __init__(self, vim: NvimFacade, name: Optional[str], parent: Optional[Machine]) -> None:
        super().__init__(vim, UniteTransitions, name, parent)
        self._unite_ready = False

    def prepare(self, msg: Message) -> None:
        if not self._unite_ready and isinstance(msg, UniteMessage):
            self._setup_unite()

    def _setup_unite(self) -> None:
        entities.traverse(lambda a: NvimIO(a.define), NvimIO).attempt(self.vim)
        self._unite_ready = True

__all__ = ('Plugin')
