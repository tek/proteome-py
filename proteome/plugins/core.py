from pathlib import Path  # type: ignore

from tryp import List

from trypnv.machine import Message, handle, may_handle, message

from proteome.state import ProteomeComponent
from proteome.project import Project
from proteome.env import Env


Init = message('Init')
Ready = message('Ready')
AddByIdent = message('AddByIdent', 'ident')
RemoveByIdent = message('RemoveByIdent', 'ident')
Create = message('Create', 'name', 'root')
Next = message('Next')
Prev = message('Prev')
SetRoot = message('SetRoot')
SwitchRoot = message('SwitchRoot', 'name')
Save = message('Save')


class Show(Message):

    def __init__(self, *names):
        self.names = names


class Plugin(ProteomeComponent):

    @may_handle(Init)
    def init(self, env: Env, msg):
        return env + env.analyzer(self.vim).current  # type: ignore

    @handle(AddByIdent)
    def add_by_ident(self, env: Env, msg):
        return env.loader.by_ident(msg.ident)\
            .or_else(env.loader.resolve_ident(msg.ident))\
            .map(env.add)

    @may_handle(RemoveByIdent)
    def remove_by_ident(self, env: Env, msg):
        return env - msg.ident

    @may_handle(Create)
    def create(self, env: Env, msg):
        return env + Project(msg.name, Path(msg.root))

    @may_handle(Show)
    def show(self, env: Env, msg: Show):
        lines = env.projects.show(List.wrap(msg.names))
        header = List('Projects:')  # type: List[str]
        self.vim.echo('\n'.join(header + lines))

    @may_handle(SwitchRoot)
    def switch_root(self, env: Env, msg):
        env.project(msg.name)\
            .map(lambda a: a.root)\
            .foreach(self.vim.switch_root)  # type: ignore

    @may_handle(Next)
    def next(self, env: Env, msg):
        return env.inc(1), SetRoot()

    @may_handle(Prev)
    def prev(self, env: Env, msg):
        return env.inc(-1), SetRoot()

    @handle(SetRoot)
    def set_root(self, env: Env, msg):
        return env.current.map(lambda a: (env, SwitchRoot(a.name)))

__all__ = ['Create', 'AddByIdent', 'Plugin', 'Show', 'Init', 'Ready']
