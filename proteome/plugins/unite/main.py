from ribosome.machine import may_handle

from amino import List, Map

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.plugins.unite.data import (UniteSelectAdd, UniteSelectAddAll,
                                         UniteProjects, UniteSource, UniteKind,
                                         Id, UniteMessage)


class UniteTransitions(ProteomeTransitions):

    def unite_cmd(self, cmd):
        args = ' '.join(self.msg.unite_args)
        self.vim.cmd('Unite {} {}'.format(cmd, args))

    @may_handle(UniteSelectAdd)
    def select_add(self):
        self.unite_cmd(Id.addable)

    @may_handle(UniteSelectAddAll)
    def select_add_all(self):
        self.unite_cmd(Id.all_addable)

    @may_handle(UniteProjects)
    def projects(self):
        self.unite_cmd(Id.projects)


class Plugin(ProteomeComponent):
    Transitions = UniteTransitions

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._unite_ready = False

    def prepare(self, msg):
        if (not self._unite_ready and isinstance(msg, UniteMessage)):
            self._setup_unite()

    def _setup_unite(self):
        addable = UniteSource(Id.addable, Id.addable_candidates, Id.addable)
        all_addable = UniteSource(Id.all_addable, Id.all_addable_candidates,
                                  Id.addable)
        add_action = Map(name='add', handler=Id.add_project,
                         desc='add project')
        add_pro = UniteKind(Id.addable, List(add_action))
        projects = UniteSource(Id.projects, Id.projects_candidates, Id.project)
        delete_action = Map(name='delete', handler=Id.delete_project,
                            desc='delete project')
        activate_action = Map(name='activate', handler=Id.activate_project,
                              desc='activate project', is_selectable=0)
        project = UniteKind(Id.project, List(activate_action, delete_action))
        addable.define(self.vim)
        all_addable.define(self.vim)
        add_pro.define(self.vim)
        projects.define(self.vim)
        project.define(self.vim)
        self._unite_ready = True

__all__ = ('Plugin')
