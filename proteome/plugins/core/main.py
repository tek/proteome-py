import re
from pathlib import Path

from fn import F, _

from amino import List, Map, Empty, may
from amino.lazy import lazy

from ribosome.machine import handle, may_handle, Error, Info, Nop
from ribosome.process import JobClient

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.project import Project, mkpath
from proteome.git import Git
from proteome.plugins.core.message import (
    StageI, StageIV, Add, RemoveByIdent, Create, Next, Prev,
    SetProject, SetProjectIdent, SetProjectIndex, SwitchRoot, Added,
    Removed, ProjectChanged, BufEnter, Initialized, MainAdded, Show,
    AddByParams, CloneRepo)


@may
def valid_index(i, total):
    if i >= 0 and i < total:
        return i
    elif i < 0 and -i <= total:
        return total + i


class CoreTransitions(ProteomeTransitions):

    def _no_such_ident(self, ident: str, params):
        return 'no project found matching \'{}\''.format(ident)

    @may_handle(StageI)
    def stage_1(self):
        main = self.data.analyzer(self.vim).main
        return Add(main), MainAdded().pub  # type: ignore

    @may_handle(StageIV)
    def stage_4(self):
        return BufEnter(self.vim.buffer).pub, Initialized().pub

    @may_handle(Initialized)
    def initialized(self):
        return self.data.set(initialized=True), SwitchRoot(False)

    @may_handle(MainAdded)
    def main_added(self):
        self.data.main.foreach(self._setup_main)

    def _setup_main(self, pro: Project):
        self.vim.vars.set_p('main_name', pro.name)
        self.vim.vars.set_p('main_ident', pro.ident)
        self.vim.vars.set_p('main_type', pro.tpe | 'none')
        self.vim.vars.set_p('main_types', pro.all_types)

    @may_handle(AddByParams)
    def add_by_params(self):
        options = Map(self.msg.options)
        ident = self.msg.ident
        return (
            (options.get('root') /
                mkpath //
                F(self.data.loader.from_params, ident, params=options))
            .or_else(
                self.data.loader.by_ident(ident)
                .or_else(self.data.loader.resolve_ident(
                    ident, options, self.data.main_type))
            ) /
            Add |
            Error(self._no_such_ident(ident, options))
        )

    @may_handle(Add)
    def add(self):
        if self.msg.project not in self.data:
            return (self.data.add(self.msg.project),
                    Added(self.msg.project).pub)

    @may_handle(Added)
    def added(self):
        self.vim.vars.set_p('added_project', self.msg.project.json)
        self.vim.vars.set_p('projects', self.data.projects.json)
        self.vim.pautocmd('Added')
        if self.data.initialized:
            return SetProjectIndex(-1)

    @handle(RemoveByIdent)
    def remove_by_ident(self):
        id = self.msg.ident
        target = self.data.projects.index_of_ident(id) | float('nan')
        cur = self.data.current_index
        switch = SetProjectIndex(0) if target == cur else Nop()
        data = self.data.set_index(cur - 1) if target < cur else self.data
        return self.data.project(id)\
            .map(lambda a: (data - a, Removed(a).pub, switch))

    @may_handle(Removed)
    def removed(self):
        self.vim.vars.set_p('projects', self.data.projects.json)
        self.vim.pautocmd('Removed')
        return Info('Removed project {}'.format(self.msg.project.ident))

    @may_handle(Create)
    def create(self):
        return self.data + Project.of(self.msg.name, Path(self.msg.root))

    @may_handle(Show)
    def show(self):
        lines = self.data.projects.show(List.wrap(self.msg.names))
        header = List('Projects:')  # type: List[str]
        return Info('\n'.join(header + lines))

    @may_handle(SetProject)
    def set_project(self):
        if isinstance(self.msg.ident, str):
            if self.msg.ident in self.data:
                return SetProjectIdent(self.msg.ident)
            elif self.msg.ident.isdigit():
                return SetProjectIndex(int(self.msg.ident))
            else:
                err = '\'{}\' is not a valid project identifier'
                return Error(err.format(self.msg.ident))

    @handle(SetProjectIndex)
    def set_project_index(self):
        return (
            valid_index(self.msg.index, self.data.project_count) /
            self.data.set_index /
            (lambda a: (a, SwitchRoot()))
        )

    @handle(SetProjectIdent)
    def set_project_ident(self):
        return self.data.set_index_by_ident(self.msg.ident)\
            .map(lambda a: (a, SwitchRoot()))

    @handle(SwitchRoot)
    def switch_root(self):
        def go(pro: Project):
            self.vim.switch_root(pro.root)  # type: ignore
            pc = ProjectChanged(pro)
            info = 'switched root to {}'
            return ((pc, Info(info.format(pro.ident))) if self.msg.notify
                    else pc)
        return (self.data.current.map(go) if self.data.initialized else
                Empty())

    @may_handle(ProjectChanged)
    def project_changed(self):
        self.vim.vars.set_p('active', self.msg.project.json)

    @may_handle(Next)
    def next(self):
        return self.data.inc(1), SwitchRoot()

    @may_handle(Prev)
    def prev(self):
        return self.data.inc(-1), SwitchRoot()

    @may_handle(Error)
    def error(self):
        self.log.error(self.msg.message)

    @may_handle(Info)
    def info(self):
        self.log.info(self.msg.message)

    # TODO make configurable (destination dir)
    @handle(CloneRepo)
    def clone_repo(self):
        uri = self.msg.uri
        name = self.msg.options.get('name')\
            .or_else(self._clone_repo_name(uri))
        url = self._clone_url(uri)
        return (
            self.data.main_clone_dir.ap2(name, _ / _)
            .to_either('invalid parameter: {}'.format(uri)) /
            F(self._clone_repo, url)
        )

    def _clone_url(self, uri):
        return uri if uri.startswith('http') else self._github_url(uri)

    def _github_url(self, uri):
        return 'https://github.com/{}'.format(uri)

    def _clone_repo_name(self, uri):
        return (
            List.wrap(uri.split('/'))
            .lift(-1) /
            F(re.sub, '\.git$', '')
        )

    @property
    def cloner(self) -> Git:
        return self._cloner  # type: ignore

    @lazy
    def _cloner(self):
        return Git(self.vim)

    async def _clone_repo(self, url: str, target):
        ident = '/'.join(str(target).split('/')[-2:])
        client = JobClient(cwd=Path.home(), name=self.name)
        res = await self.cloner.clone(client, url, target)
        return res.either(
            AddByParams(ident, Map()).pub,
            Error('failed to clone {} to {}'.format(url, target)).pub
        )


class Plugin(ProteomeComponent):
    Transitions = CoreTransitions

__all__ = ('Plugin',)
