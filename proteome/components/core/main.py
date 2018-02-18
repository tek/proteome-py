import re
from pathlib import Path
from typing import Generator

from amino import List, Map, Empty, may, _, L, __, Try, Maybe, Just
from amino.lazy import lazy
from amino.do import tdo
from amino.dat import Dat

from ribosome.machine.transition import handle, may_handle
from ribosome.machine.messages import Error, Info, Nop, Stage1, Stage2, Stage3, Stage4, Quit
from ribosome.process import JobClient
from ribosome.machine.transition import may_fallback
from ribosome.machine.state import Component
from ribosome.machine import trans
from ribosome.nvim import NvimIO
from ribosome.nvim.io import NvimIOState
from ribosome.machine.state_a import store_json_data, load_json_data
from ribosome.machine.message_base import Message

from proteome.project import Project, mkpath
from proteome.git import Git
from proteome.components.core.message import (Add, RemoveByIdent, Create, Next, Prev, SetProject, SetProjectIdent,
                                              SetProjectIndex, SwitchRoot, Added, Removed, ProjectChanged, BufEnter,
                                              Initialized, MainAdded, Show, AddByParams, CloneRepo, Save, Load)
from proteome import Env


@may
def valid_index(i, total):
    if i >= 0 and i < total:
        return i
    elif i < 0 and -i <= total:
        return total + i


class BuffersState(Dat['BuffersState']):

    def __init__(self, buffers: List[str], current: Maybe[str]) -> None:
        self.buffers = buffers
        self.current = current


@tdo(NvimIOState[Env, None])
def persist_buffers() -> Generator:
    is_file = lambda p: Try(Path, p).map(__.is_file()).true
    filter_files = lambda bs: bs.map(_.name).filter(is_file)
    b = yield NvimIOState.io(_.buffers)
    files = filter_files(b.filter(_.listed))
    buf = yield NvimIOState.io(_.buffer)
    current = filter_files(Just(buf))
    state = BuffersState(files, current)
    yield store_json_data('buffers', state)


@tdo(NvimIOState[Env, None])
def load_buffers(state: BuffersState) -> Generator:
    yield NvimIOState.lift(state.buffers.traverse(lambda a: NvimIO.cmd_sync(f'badd {a}'), NvimIO))
    cmdline_arg_count = yield NvimIOState.lift(NvimIO.call('argc'))
    if cmdline_arg_count == 0:
        yield NvimIOState.lift(state.current / (lambda a: NvimIO.cmd(f'edit {a}')) | NvimIO.pure(None))


@tdo(NvimIOState[Env, None])
def load_persisted_buffers() -> Generator:
    data = yield load_json_data('buffers')
    yield data.cata(lambda a: NvimIOState.pure(None), load_buffers)


class Core(Component):

    def _no_such_ident(self, ident: str, params):
        return 'no project found matching \'{}\''.format(ident)

    @may_handle(Stage1)
    def stage_1(self):
        main = self.data.analyzer(self.vim).main
        return Add(main), MainAdded().pub

    @trans.one(Stage2, trans.st, trans.m)
    @tdo(NvimIOState[Env, Maybe[Message]])
    def stage_2(self) -> Generator:
        settings = yield NvimIOState.inspect(_.settings)
        load = yield NvimIOState.lift(settings.load_buffers.value_or_default)
        yield NvimIOState.pure(load.m(Load()))

    @may_fallback(Stage3)
    def stage_3(self):
        pass

    @trans.multi(Stage4, trans.nio)
    def stage_4(self):
        return NvimIO(lambda v: List(BufEnter(v.buffer).pub, Initialized().pub))

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
             L(self.data.loader.from_params)(ident, _, params=options))
            .or_else(
                self.data.loader.by_ident(ident)
                .or_else(self.data.loader.resolve_ident(ident, options, self.data.main_type))
            ) /
            Add.from_msg(self.msg) |
            Error(self._no_such_ident(ident, options))
        )

    @may_handle(Add)
    def add(self):
        if self.msg.project not in self.data:
            return self.data.add(self.msg.project), Added.from_msg(self.msg)(self.msg.project).pub

    @may_handle(Added)
    def added(self):
        self.vim.vars.set_p('added_project', self.msg.project.json)
        self.vim.vars.set_p('projects', self.data.projects.json)
        self.vim.pautocmd('Added')
        if self.data.initialized and not self.msg.bang:
            return SetProjectIndex(-1)

    @handle(RemoveByIdent)
    def remove_by_ident(self):
        id = self.msg.ident
        target = self.data.projects.index_of_ident(id) | float('nan')
        cur = self.data.current_index
        switch = SetProjectIndex(0) if target == cur else Nop()
        data = self.data.set_index(cur - 1) if target < cur else self.data
        return self.data.project(id).map(lambda a: (data - a, Removed(a).pub, switch))

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
            path = pro.root
            p = str(path)
            self.vim.cd(p)
            self.vim.pautocmd('SwitchedRoot')
            self.vim.vars.set_p('root_dir', p)
            pc = ProjectChanged(pro)
            info = 'switched root to {}'
            return (pc, Info(info.format(pro.ident))) if self.msg.notify else pc
        return self.data.current.map(go) if self.data.initialized else Empty()

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
            self.data.main_clone_dir.ap2(name, lambda dir, n: dir / n)
            .to_either('invalid parameter: {}'.format(uri)) /
            L(self._clone_repo)(url, _)
        )

    @may_handle(BufEnter)
    def buf_enter(self):
        ''' dummy handler to prevent error message in tests when ctags plugin is not active
        '''
        pass

    @trans.unit(Quit)
    def quit(self) -> None:
        '''fallback handler
        '''
        pass

    @trans.unit(Save, trans.st)
    def save(self) -> NvimIOState[Env, None]:
        return persist_buffers()

    @trans.unit(Load, trans.st)
    def load(self) -> NvimIOState[Env, None]:
        return load_persisted_buffers()

    def _clone_url(self, uri):
        return uri if uri.startswith('http') else self._github_url(uri)

    def _github_url(self, uri):
        return 'https://github.com/{}'.format(uri)

    def _clone_repo_name(self, uri):
        return (
            List.wrap(uri.split('/'))
            .lift(-1) /
            L(re.sub)('\.git$', '', _)
        )

    @property
    def cloner(self) -> Git:
        return self._cloner

    @lazy
    def _cloner(self) -> Git:
        return Git(self.vim)

    async def _clone_repo(self, url: str, target):
        ident = '/'.join(str(target).split('/')[-2:])
        client = JobClient(cwd=Path.home(), name=self.name)
        res = await self.cloner.clone(client, url, target)
        return res.either(
            AddByParams(ident, Map()).pub,
            Error('failed to clone {} to {}'.format(url, target)).pub
        )

__all__ = ('Core',)
