from pathlib import Path  # type: ignore

from fn import _  # type: ignore

from tryp import List

from trypnv.machine import Message, handle, may_handle, message

from proteome.state import ProteomeComponent
from proteome.project import Project
from proteome.env import Env


Init = message('Init')
Ready = message('Ready')
Add = message('Add', 'project')
AddByIdent = message('AddByIdent', 'ident')
RemoveByIdent = message('RemoveByIdent', 'ident')
Create = message('Create', 'name', 'root')
Next = message('Next')
Prev = message('Prev')
SetRoot = message('SetRoot')
SetRootIndex = message('SetRootIndex', 'index')
SwitchRoot = message('SwitchRoot', 'name')
Save = message('Save')
Added = message('Added', 'project')
Removed = message('Removed', 'project')
ProjectChanged = message('ProjectChanged', 'project')
BufEnter = message('BufEnter', 'buffer')
Initialized = message('Initialized')


class Show(Message):

    def __init__(self, *names):
        self.names = names


class Plugin(ProteomeComponent):

    def _no_such_ident(self, ident: str):
        self.log.error('no project found matching \'{}\''.format(ident))

    @may_handle(Init)
    def init(self, env: Env, msg):
        return (Add(env.analyzer(self.vim).current),  # type: ignore
                BufEnter(self.vim.current_buffer).pub,
                SetRoot())

    @may_handle(Ready)
    def ready(self, env, msg):
        return Initialized()

    @may_handle(Initialized)
    def initialized(self, env, msg):
        return env.set(initialized=True)

    @handle(AddByIdent)
    def add_by_ident(self, env: Env, msg):
        return env.loader.by_ident(msg.ident)\
            .or_else(env.loader.resolve_ident(msg.ident))\
            .map(Add)\
            .error(lambda: self._no_such_ident(msg.ident))

    @may_handle(Add)
    def add(self, env: Env, msg):
        if msg.project not in env:
            return env.add(msg.project), Added(msg.project).pub

    @may_handle(Added)
    def added(self, env, msg):
        self.vim.set_pvar('added_project', str(msg.project.root))
        self.vim.pautocmd('Added')
        if env.initialized:
            return SetRootIndex(-1)

    @handle(RemoveByIdent)
    def remove_by_ident(self, env: Env, msg):
        return env.project(msg.ident)\
            .map(lambda a: (env - a, Removed(a).pub))

    @may_handle(Create)
    def create(self, env: Env, msg):
        return env + Project(msg.name, Path(msg.root))

    @may_handle(Show)
    def show(self, env: Env, msg: Show):
        lines = env.projects.show(List.wrap(msg.names))
        header = List('Projects:')  # type: List[str]
        self.vim.echo('\n'.join(header + lines))

    @handle(SwitchRoot)
    def switch_root(self, env: Env, msg):
        pro = env.project(msg.name)
        pro.map(_.root)\
            .foreach(self.vim.switch_root)  # type: ignore
        if env.initialized:
            info = 'switched root to {}'
            pro.foreach(lambda a: self.log.info(info.format(a.ident)))
        return pro.map(ProjectChanged)

    @handle(SetRoot)
    def set_root(self, env: Env, msg):
        return env.current.map(_.name).map(SwitchRoot)

    @may_handle(SetRootIndex)
    def set_root_index(self, env, msg):
        return env.set_index(msg.index), SetRoot()

    @may_handle(Next)
    def next(self, env: Env, msg):
        return env.inc(1), SetRoot()

    @may_handle(Prev)
    def prev(self, env: Env, msg):
        return env.inc(-1), SetRoot()

__all__ = ['Create', 'AddByIdent', 'Plugin', 'Show', 'Init', 'Ready']
