import abc

from trypnv.machine import may_handle, message  # type: ignore
from trypnv import NvimFacade

from tryp import F, List, Map, _

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.logging import Logging

UniteSelectAdd = message('UniteSelectAdd')
UniteSelectAddAll = message('UniteSelectAddAll')
UniteProjects = message('UniteProjects')


class UniteEntity(Logging, metaclass=abc.ABCMeta):
    ''' set up sources and kinds dynamically.
    The python call API cannot be used, as funcrefs cannot be
    serialized.
    The callback functions must be called once so that exists()
    can see them, otherwise Unite refuses to work.
    They must be called a/sync according to their definition,
    otherwise it will silently deadlock!
    '''

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractproperty
    def tpe(self):
        ...

    @abc.abstractproperty
    def data(self):
        ...

    @property
    def _func_defs_sync(self):
        return List()

    @property
    def _func_defs_async(self):
        return List()

    def _force_function_defs(self, vim):
        force = lambda c, n: c('silent call {}()'.format(n))
        self._func_defs_sync.foreach(F(force, vim.cmd_sync))
        self._func_defs_async.foreach(F(force, vim.cmd))

    def define(self, vim: NvimFacade):
        self._force_function_defs(vim)
        vim.cmd('call unite#define_{}({})'.format(self.tpe, self.data))


class UniteSource(UniteEntity):
    _templ = '''
    {{
        'name': '{}',
        'gather_candidates': function('{}'),
        'default_kind': '{}',
    }}
    '''.replace('\n', '')

    def __init__(self, name: str, source: str, kind: str) -> None:
        super().__init__(name)
        self.source = source
        self.kind = kind

    @property
    def tpe(self):
        return 'source'

    @property
    def _func_defs_sync(self):
        return List(self.source)

    @property
    def data(self):
        return self._templ.format(self.name, self.source, self.kind)


class UniteKind(UniteEntity):
    _templ = '''
    {{
        'name': '{name}',
        'default_action': '{default}',
        'parents': [],
        'action_table': {{
            {actions}
        }}
    }}
    '''.replace('\n', '')

    _action_templ = '''
    '{name}': {{
        'func': function('{handler}'),
        'description': '{desc}',
    }}
    '''.replace('\n', '')

    @property
    def tpe(self):
        return 'kind'

    def __init__(self, name: str, actions: List[Map]) -> None:
        super().__init__(name)
        self.actions = actions
        self.default = actions.head / _['name'] | 'none'

    @property
    def _func_defs_async(self):
        return self.actions / _['handler']

    def _action(self, params):
        return self._action_templ.format(**params)

    @property
    def data(self):
        actions = self.actions.map(self._action).join(', ')
        return self._templ.format(name=self.name, actions=actions,
                                  default=self.default)


class Plugin(ProteomeComponent):
    addable_candidates = '_proteome_unite_addable'
    all_addable_candidates = '_proteome_unite_all_addable'
    projects_candidates = '_proteome_unite_projects'

    add_project = '_proteome_unite_add_project'
    remove_project = '_proteome_unite_remove_project'
    activate_project = '_proteome_unite_activate_project'

    addable = 'proteome_addable'
    all_addable = 'proteome_all_addable'
    projects = 'proteome_projects'
    project = 'proteome_project'

    unite_msgs = [UniteSelectAdd, UniteSelectAddAll, UniteProjects]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._unite_ready = False

    def prepare(self, msg):
        if (not self._unite_ready and
                type(msg) in self.unite_msgs):
            self._setup_unite()

    def _setup_unite(self):
        addable = UniteSource(self.addable, self.addable_candidates,
                              self.addable)
        all_addable = UniteSource(self.all_addable,
                                  self.all_addable_candidates, self.addable)
        add_action = Map(name='add', handler=self.add_project,
                         desc='add project')
        add_pro = UniteKind(self.addable, List(add_action))
        projects = UniteSource(self.projects, self.projects_candidates,
                               self.project)
        remove_action = Map(name='remove', handler=self.remove_project,
                            desc='remove project')
        activate_action = Map(name='activate', handler=self.activate_project,
                              desc='activate project')
        project = UniteKind(self.project, List(activate_action, remove_action))
        addable.define(self.vim)
        all_addable.define(self.vim)
        add_pro.define(self.vim)
        projects.define(self.vim)
        project.define(self.vim)
        self._unite_ready = True

    # TODO pass args from user command
    def unite_cmd(self, cmd):
        self.vim.cmd('Unite {}'.format(cmd))

    class Transitions(ProteomeTransitions):

        @may_handle(UniteSelectAdd)
        def select_add(self):
            self.machine.unite_cmd(self.machine.addable)

        @may_handle(UniteSelectAddAll)
        def select_add_all(self):
            self.machine.unite_cmd(self.machine.all_addable)

        @may_handle(UniteProjects)
        def projects(self):
            self.machine.unite_cmd(self.machine.projects)

__all__ = ('Plugin', 'UniteSelectAdd', 'UniteSelectAddAll', 'UniteProjects')
