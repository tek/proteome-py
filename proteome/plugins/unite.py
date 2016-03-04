import abc

from trypnv.machine import may_handle, message  # type: ignore
from trypnv import NvimFacade

from tryp import F, List

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.logging import Logging

UniteSelectAdd = message('UniteSelectAdd')
UniteSelectAddAll = message('UniteSelectAddAll')


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
        'name': '{}',
        'default_action': '{default}',
        'parents': [],
        'action_table': {{
            '{default}': {{
                'func': function('{}'),
                'description': '{}',
            }}
        }}
    }}
    '''.replace('\n', '')

    @property
    def tpe(self):
        return 'kind'

    def __init__(self, name: str, handler: str, default: str, desc: str
                 ) -> None:
        super().__init__(name)
        self.handler = handler
        self.default = default
        self.desc = desc

    @property
    def _func_defs_async(self):
        return List(self.handler)

    @property
    def data(self):
        return self._templ.format(self.name, self.handler, self.desc,
                                  default=self.default)


class Plugin(ProteomeComponent):
    addable_candidates = '_proteome_unite_addable'
    all_addable_candidates = '_proteome_unite_all_addable'
    add_project = '_proteome_unite_add_project'
    addable = 'proteome_addable'
    all_addable = 'proteome_all_addable'

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._unite_ready = False

    def prepare(self, msg):
        if (not self._unite_ready and
                type(msg) in [UniteSelectAdd, UniteSelectAddAll]):
            self._setup_unite()

    def _setup_unite(self):
        addable = UniteSource(self.addable, self.addable_candidates,
                              self.addable)
        all_addable = UniteSource(self.all_addable,
                                  self.all_addable_candidates, self.addable)
        add_pro = UniteKind(self.addable, self.add_project, 'add',
                            'add project')
        addable.define(self.vim)
        all_addable.define(self.vim)
        add_pro.define(self.vim)
        self._unite_ready = True

    # TODO pass args from vim command
    def unite_cmd(self, cmd):
        self.vim.cmd('Unite {}'.format(cmd))

    class Transitions(ProteomeTransitions):

        @may_handle(UniteSelectAdd)
        def select_add(self):
            self.machine.unite_cmd(self.machine.addable)

        @may_handle(UniteSelectAddAll)
        def select_add_all(self):
            self.machine.unite_cmd(self.machine.all_addable)

__all__ = ('Plugin', 'UniteSelectAdd', 'UniteSelectAddAll')
