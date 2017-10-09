from pathlib import Path

import asyncio

from kallikrein import k, Expectation, kf
from kallikrein.matchers.maybe import be_just

from amino.test import temp_dir
from amino import List, Just, _, Map

from ribosome.machine.messages import Nop, Stage1
from ribosome.machine.state import AutoRootMachine
from ribosome.nvim import NvimFacade
from ribosome.settings import Config
from ribosome.test.integration.klk import later

from proteome.project import Project, Projects, ProjectAnalyzer
from proteome.components.core import Next, Prev, RemoveByIdent, AddByParams
from proteome.components.history.data import History
from proteome.components.core.message import Create
from proteome import mk_config
from proteome.env import Env
from proteome.components.core.main import Core

from unit._support.loader import LoaderSpec
from unit._support.async import test_loop

null = Path('/dev/null')


class ProteomeSpec(LoaderSpec):
    '''transition unit tests
    create a project $create
    cycle through projects $cycle
    create ctags for two projects $ctags
    '''

    def setup(self):
        LoaderSpec.setup(self)
        asyncio.get_child_watcher()

    def _prot(self, p=Map(), b=List(), t=Map(), pros=List()):
        initial = Projects(projects=pros)
        def ctor(config: Config, vim: NvimFacade) -> Env:
            return Env(projects=initial, config=config, vim_facade=Just(vim))
        return AutoRootMachine(self.vim, mk_config(state_ctor=ctor, components=p), 'proteome').transient()

    def create(self) -> Expectation:
        name = 'proj'
        with self._prot() as prot:
            data = prot.send_sync(Create(name, null))
        p = data.projects.projects[0]
        return (k(p.name) == name) & (k(p.root) == null)

    def cycle(self) -> Expectation:
        self.vim_mock.should_receive('switch_root').and_return(None)
        name = 'proj'
        name2 = 'proj2'
        pros = List(Project.of(name, null), Project.of(name2, null))
        with self._prot(pros=pros) as prot:
            return (
                k(prot.data.current).must(be_just(pros[0])) &
                k(prot.send_sync(Next()).current).must(be_just(pros[1])) &
                k(prot.send_sync(Prev()).current).must(be_just(pros[0]))
            )

    def ctags(self) -> Expectation:
        plug_name = 'proteome.components.ctags'
        p1 = self.mk_project('pro1', 'c')
        p2 = self.mk_project('pro2', 'go')
        pros = List(p1, p2)
        with self._prot(List(plug_name), pros=pros) as prot:
            with test_loop() as loop:
                plug = prot.plugin('ctags')._get
                p1.tag_file.exists().should_not.be.ok
                p2.tag_file.exists().should_not.be.ok
                prot.plug_command('ctags', 'gen_all', List())
                def check(p):
                    plug.ctags.await_threadsafe(loop)
                    p.tag_file.exists().should.be.ok
                later(check, p1)
                later(check, p2)
                plug.ctags.ready.should.be.ok

    class history_(object):

        def setup(self):
            self.vim.vars.set_p('all_projects_history', 1)
            self.vim.vars.set('proteome_history_base', str(self.history_base))
            self.plug_name = 'proteome.components.history'
            self.main_project = self.mk_project('pro1', 'c')
            self.test_file_1 = self.main_project.root / 'test_file_1'
            self.test_content = List(
                'content_1',
                'content_2',
                'content_3',
            )

        def _three_commits(self, prot, loop):
            plug = prot.plugin('history').x
            for cont in self.test_content:
                self.test_file_1.write_text(cont)
                prot.plug_command('history', 'Commit', List())
                self._await(plug.executor, loop)

        def _await(self, executor, loop):
            self._wait(0.1)
            while not executor.ready:
                self._wait(0.1)
                executor.await_threadsafe(loop)
                self._wait(0.1)

        def init(self):
            def check_head(p):
                (self.history_base / p.fqn / 'HEAD').exists().should.be.ok
            p1 = self.main_project
            p2 = self.mk_project('pro2', 'go')
            pros = List(p1, p2)
            with self._prot(List(self.plug_name), pros=pros) as prot:
                prot.plug_command('history', 'Stage4', List())
                later(lambda: check_head(p1))
                check_head(p2)

        def commit(self):
            p1 = self.main_project
            p2 = self.mk_project('pro2', 'go')
            pros = List(p1, p2)
            hist = History(self.history_base)
            with self._prot(List(self.plug_name), pros=pros) as prot:
                with test_loop() as loop:
                    prot.plug_command('history', 'Stage4', List())
                    plug = prot.plugin('history').x
                    self.test_file_1.write_text('test')
                    prot.plug_command('history', 'Commit', List())
                    self._await(plug.executor, loop)
            (hist.repo(p1) / _.history // _.head / repr).should.just

        def prev_next(self):
            p1 = self.main_project
            p2 = self.mk_project('pro2', 'go')
            pros = List(p1, p2)
            with self._prot(List(self.plug_name), pros=pros) as prot:
                with test_loop() as loop:
                    prot.plug_command('history', 'Stage4', List())
                    self._three_commits(prot, loop)
                    prot.plug_command('history', 'HistoryLog', List())
                    prot.plug_command('history', 'HistoryPrev', List())
                    prot.plug_command('history', 'HistoryLog', List())
                    later(lambda: self.test_file_1.read_text()
                          .should.equal(self.test_content[1]))
                    prot.plug_command('history', 'HistoryNext', List())
                    later(lambda: self.test_file_1.read_text()
                          .should.equal(self.test_content[2]))

    def current_project(self):
        p = self.pypro1_root
        flexmock(ProjectAnalyzer)\
            .should_receive('main_dir')\
            .and_return(Just(p))
        ctx = self._prot(b=List(self.project_base), t=self.type_bases)
        target = Project.of(self.pypro1_name, p, Just(self.pypro1_type))
        with ctx as prot:
            prot.send_sync(Stage1())
            prot.send_sync(Nop())\
                .projects.projects.head\
                .should.equal(Just(target))

    def add_remove_project(self):
        ctx = self._prot(List(), List(self.project_base), self.type_bases)
        with ctx as prot:
            prot.send_sync(AddByParams(self.pypro1_name, Map()))\
                .project(self.pypro1_name)\
                .map(_.root)\
                .should.contain(self.pypro1_root)
            prot.send_sync(RemoveByIdent(self.pypro1_name))\
                .all_projects.should.be.empty

    def add_by_params(self):
        tpe = 'ptype'
        name = 'pname'
        root = temp_dir('proteome', 'add_by_params')
        params = Map(
            type=tpe,
            root=root
        )
        with self._prot() as prot:
            ret = prot.send_sync(AddByParams(name, params))
            (ret.project(name) / _.root).should.contain(root)

__all__ = ('ProteomeSpec',)
