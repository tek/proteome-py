from amino import List, Map

from ribosome.machine.transition import may_handle
from ribosome.machine.state import Component, ComponentMachine

from proteome.components.unite.data import (UniteSelectAdd, UniteSelectAddAll,
                                         UniteProjects, UniteSource, UniteKind,
                                         UniteNames, UniteMessage)


class UniteTransitions(Component):

    def unite_cmd(self, cmd):
        args = ' '.join(self.msg.unite_args)
        self.vim.cmd('Unite {} {}'.format(cmd, args))

    @may_handle(UniteSelectAdd)
    def select_add(self):
        self.unite_cmd(UniteNames.addable)

    @may_handle(UniteSelectAddAll)
    def select_add_all(self):
        self.unite_cmd(UniteNames.all_addable)

    @may_handle(UniteProjects)
    def projects(self):
        self.unite_cmd(UniteNames.projects)


class Plugin(ComponentMachine):
    Transitions = UniteTransitions

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._unite_ready = False

    def prepare(self, msg):
        if (not self._unite_ready and isinstance(msg, UniteMessage)):
            self._setup_unite()

    def _setup_unite(self):
        addable = UniteSource(UniteNames.addable, UniteNames.addable_candidates, UniteNames.addable)
        all_addable = UniteSource(UniteNames.all_addable, UniteNames.all_addable_candidates, UniteNames.addable)
        add_action = Map(name='add', handler=UniteNames.add_project, desc='add project')
        add_pro = UniteKind(UniteNames.addable, List(add_action))
        projects = UniteSource(UniteNames.projects, UniteNames.projects_candidates, UniteNames.project)
        delete_action = Map(name='delete', handler=UniteNames.delete_project, desc='delete project')
        activate_action = Map(name='activate', handler=UniteNames.activate_project, desc='activate project',
                              is_selectable=0)
        project = UniteKind(UniteNames.project, List(activate_action, delete_action))
        addable.define(self.vim)
        all_addable.define(self.vim)
        add_pro.define(self.vim)
        projects.define(self.vim)
        project.define(self.vim)
        self._unite_ready = True

__all__ = ('Plugin')
