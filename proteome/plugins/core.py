from pathlib import Path  # type: ignore

from tryp import List

from trypnv.machine import Message, handle, may_handle, message

from proteome.state import ProteomeComponent
from proteome.project import Project
from proteome.env import Env


Init = message('Init')
Ready = message('Ready')
Add = message('Add')
AddByName = message('AddByName', 'name')
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
        anal = env.analyzer(self.vim)  # type: ignore
        return env.add(anal.current)

    @may_handle(Add)
    def add(self, env: Env, msg):
        pass

    @handle(AddByName)
    def add_by_name(self, env: Env, msg):
        return env.loader.by_name(msg.name)\
            .map(lambda a: env.set(projects=env.projects + a))

    @may_handle(Create)
    def create(self, env: Env, msg):
        new = env.projects + Project(msg.name, Path(msg.root))
        return env.set(projects=new)

    @may_handle(Show)
    def show(self, env: Env, msg: Show):
        lines = env.projects.show(List.wrap(msg.names))
        header = List('Projects:')  # type: List[str]
        self.vim.echo('\n'.join(header + lines))

    @may_handle(SwitchRoot)
    def switch_root(self, env: Env, msg):
        env.project_by_name(msg.name)\
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

__all__ = ['Add', 'Create', 'AddByName', 'Plugin', 'Show']
