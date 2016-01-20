from pathlib import Path  # type: ignore

from fn import _  # type: ignore

from tryp import List, Map, Empty

from trypnv.machine import handle, may_handle, message, Error  # type: ignore

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
Clone = message('Clone', 'url', 'params')


class Plugin(ProteomeComponent):

    def _no_such_ident(self, ident: str, params):
        self.log.error('no project found matching \'{}\''.format(ident))

    @may_handle(StageI)
    def stage_1(self, env: Env, msg):
        main = env.analyzer(self.vim).main
        return Add(main), MainAdded().pub  # type: ignore

    @may_handle(StageIV)
    def stage_4(self, env, msg):
        return BufEnter(self.vim.buffer).pub, Initialized().pub

    @may_handle(Initialized)
    def initialized(self, env, msg):
        return env.set(initialized=True), SwitchRoot()

    @may_handle(MainAdded)
    def main_added(self, env, msg):
        env.main.foreach(self._setup_main)

    def _setup_main(self, pro: Project):
        self.vim.set_pvar('main_name', pro.name)
        self.vim.set_pvar('main_ident', pro.ident)
        self.vim.set_pvar('main_type', pro.tpe | 'none')
        self.vim.set_pvar('main_types', pro.all_types)

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

    # TODO switch project if removed current
    @handle(RemoveByIdent)
    def remove_by_ident(self, env: Env, msg):
        return env.project(msg.ident)\
            .map(lambda a: (env - a, Removed(a).pub))

    @may_handle(Create)
    def create(self, env: Env, msg):
        return env + Project.of(msg.name, Path(msg.root))

    @may_handle(Show)
    def show(self, env: Env, msg: Show):
        lines = env.projects.show(List.wrap(msg.names))
        header = List('Projects:')  # type: List[str]
        self.log.info('\n'.join(header + lines))

    @may_handle(SetProject)
    def set_project(self, env: Env, msg):
        if isinstance(msg.ident, str):
            if msg.ident in env:
                return SetProjectIdent(msg.ident)
            elif msg.ident.isdigit():
                return SetProjectIndex(int(msg.ident))
            else:
                err = '\'{}\' is not a valid project identifier'
                return Error(err.format(msg.ident))

    @may_handle(SetProjectIndex)
    def set_project_index(self, env, msg):
        if msg.index < env.project_count:
            return env.set_index(msg.index), SwitchRoot()

    @handle(SetProjectIdent)
    def set_project_ident(self, env: Env, msg):
        return env.set_index_by_ident(msg.ident)\
            .map(lambda a: (a, SwitchRoot()))

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

    @may_handle(Error)
    def error(self, env, msg):
        self.log.error(msg.message)

    @may_handle(Clone)
    def clone(self, uri):
        if uri.startswith('http'):
            self._clone_url(uri)
        else:
            self._clone_github(uri)

    def _clone_url(self, url: str):
        pass

    def _clone_github(self, path: str):
        self._clone_uri('https://github.com/{}'.format(path))

__all__ = ['Create', 'AddByParams', 'Plugin', 'Show', 'StageI', 'StageII',
           'StageIII', 'AddByParams', 'RemoveByIdent', 'Next', 'Prev',
           'SetProjectIndex', 'Save', 'Added', 'Removed', 'ProjectChanged',
           'BufEnter', 'Initialized', 'MainAdded', 'StageIV']
