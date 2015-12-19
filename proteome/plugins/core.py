from pathlib import Path  # type: ignore

from fn import _  # type: ignore

from tryp import List, Map, Empty

from trypnv.machine import Message, handle, may_handle, message  # type: ignore

from proteome.state import ProteomeComponent
from proteome.project import Project, mkpath
from proteome.env import Env

StageI = message('StageI')
StageII = message('StageII')
StageIII = message('StageIII')
StageIV = message('StageIV')
Add = message('Add', 'project')
RemoveByIdent = message('RemoveByIdent', 'ident')
Create = message('Create', 'name', 'root')
Next = message('Next')
Prev = message('Prev')
SetProject = message('SetProject', 'ident')
SetProjectIdent = message('SetProjectIdent', 'ident')
SetProjectIndex = message('SetProjectIndex', 'index')
SwitchRoot = message('SwitchRoot')
Save = message('Save')
Added = message('Added', 'project')
Removed = message('Removed', 'project')
ProjectChanged = message('ProjectChanged', 'project')
BufEnter = message('BufEnter', 'buffer')
Initialized = message('Initialized')
MainAdded = message('MainAdded')
Show = message('Show', varargs='names')
AddByParams = message('AddByParams', 'ident', 'params')


class Plugin(ProteomeComponent):

    def _no_such_ident(self, ident: str, params):
        self.log.error('no project found matching \'{}\''.format(ident))

    @may_handle(StageI)
    def stage_1(self, env: Env, msg):
        main = env.analyzer(self.vim).main
        return Add(main), MainAdded().pub  # type: ignore

    @may_handle(StageII)
    def stage_2(self, env, msg):
        return SwitchRoot()

    @may_handle(StageIV)
    def stage_4(self, env, msg):
        return BufEnter(self.vim.current_buffer).pub, Initialized().pub

    @may_handle(Initialized)
    def initialized(self, env, msg):
        return env.set(initialized=True)

    @handle(AddByParams)
    def add_by_params(self, env: Env, msg):
        params = Map(msg.params)
        return params.get('root').map(mkpath)\
            .map(lambda a: env.loader.from_params(msg.ident, a, params))\
            .get_or_else(
                env.loader.by_ident(msg.ident)
                .or_else(env.loader.resolve_ident(msg.ident, params))
            )\
            .map(Add)\
            .error(lambda: self._no_such_ident(msg.ident, params))

    @may_handle(Add)
    def add(self, env: Env, msg):
        if msg.project not in env:
            return env.add(msg.project), Added(msg.project).pub

    @may_handle(Added)
    def added(self, env, msg):
        self.vim.set_pvar('added_project', msg.project.json)
        self.vim.set_pvar('projects', env.projects.json)
        self.vim.pautocmd('Added')
        if env.initialized:
            return SetProjectIndex(-1)

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

    @may_handle(SetProject)
    def set_project(self, env: Env, msg):
        if isinstance(msg.ident, int):
            return SetProjectIndex(msg.ident)
        elif isinstance(msg.ident, str):
            return SetProjectIdent(msg.ident)

    @may_handle(SetProjectIndex)
    def set_project_index(self, env, msg):
        if msg.index < env.project_count:
            return env.set_index(msg.index), SwitchRoot()

    @may_handle(SetProjectIdent)
    def set_project_ident(self, env: Env, msg):
        return env.set_index_by_ident(msg.ident)

    @handle(SwitchRoot)
    def switch_root(self, env: Env, msg):
        if env.initialized:
            pro = env.current
            pro.map(_.root)\
                .foreach(self.vim.switch_root)  # type: ignore
            info = 'switched root to {}'
            pro.foreach(lambda a: self.log.info(info.format(a.ident)))
            return pro.map(ProjectChanged)
        else:
            return Empty()

    @may_handle(Next)
    def next(self, env: Env, msg):
        return env.inc(1), SwitchRoot()

    @may_handle(Prev)
    def prev(self, env: Env, msg):
        return env.inc(-1), SwitchRoot()

__all__ = ['Create', 'AddByParams', 'Plugin', 'Show', 'StageI', 'StageII',
           'StageIII', 'AddByParams', 'RemoveByIdent', 'Next', 'Prev',
           'SetProjectIndex', 'Save', 'Added', 'Removed', 'ProjectChanged',
           'BufEnter', 'Initialized', 'MainAdded']
