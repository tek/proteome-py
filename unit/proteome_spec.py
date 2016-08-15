from pathlib import Path

import asyncio

from flexmock import flexmock  # NOQA

from tryp import List, Just, _, Map

from trypnv.machine import Nop

from proteome.nvim_plugin import Create
from proteome.project import Project, Projects, ProjectAnalyzer
from proteome.plugins.core import (Next, Prev, StageI, RemoveByIdent,
                                   AddByParams)
from proteome.main import Proteome
from proteome.plugins.history.data import History

from unit._support.loader import LoaderSpec
from unit._support.async import test_loop

from tryp.test import temp_dir, later

null = Path('/dev/null')


class DictProteome(Proteome):
    _data_type = dict

    @property
    def init(self):
        return dict()


class Proteome_(LoaderSpec):

    def setup(self):
        super().setup()
        asyncio.get_child_watcher()

    def _prot(self, p=List(), b=List(), t=Map(), pros=List()):
        initial = Just(Projects(projects=pros))
        return Proteome(self.vim, self.config, p, b, t, initial).transient()

    def create(self):
        name = 'proj'
        with self._prot() as prot:
            data = prot.send_sync(Create(name, null))
        p = data.projects.projects[0]
        p.name.should.equal(name)
        p.root.should.equal(null)

    def cycle(self):
        self.vim_mock.should_receive('switch_root').and_return(None)
        name = 'proj'
        name2 = 'proj2'
        pros = List(Project.of(name, null), Project.of(name2, null))
        with self._prot(pros=pros) as prot:
            prot.data.current.should.equal(Just(pros[0]))
            prot.send_sync(Next())\
                .current.should.equal(Just(pros[1]))
            prot.send_sync(Prev())\
                .current.should.equal(Just(pros[0]))

    def command(self):
        plug = 'unit._support.test_plug'
        prot = DictProteome(self.vim, null, List(plug), List(), Map())
        prot.start_wait()
        data = 'message_data'
        prot.plug_command('test_plug', 'do', [data])
        later(lambda: prot.data.should.have.key(data).being.equal(data))
        prot.stop()

    def invalid_command(self):
        plug = 'unit._support.test_plug'
        prot = DictProteome(self.vim, null, List(plug), List(), Map())
        prot.start_wait()
        data = 'message_data'
        prot.plug_command('test_plug', 'do', [data])
        prot.plug_command('test_plug', 'dont', [data])
        later(lambda: prot.data.should.have.key(data).being.equal(data))
        prot.stop()

    def ctags(self):
        plug_name = 'proteome.plugins.ctags'
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
                later(lambda: check(p1))
                later(lambda: check(p2))
                plug.ctags.ready.should.be.ok

    class history_(object):

        def setup(self):
            self.vim.set_pvar('all_projects_history', 1)
            self.vim.vars['proteome_history_base'] = str(self.history_base)
            self.plug_name = 'proteome.plugins.history'
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
                prot.plug_command('history', 'StageIV', List())
                later(lambda: check_head(p1))
                check_head(p2)

        def commit(self):
            p1 = self.main_project
            p2 = self.mk_project('pro2', 'go')
            pros = List(p1, p2)
            hist = History(self.history_base)
            with self._prot(List(self.plug_name), pros=pros) as prot:
                with test_loop() as loop:
                    prot.plug_command('history', 'StageIV', List())
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
                    prot.plug_command('history', 'StageIV', List())
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
            prot.send_sync(StageI())
            prot.send_sync(Nop())\
                .projects.projects.head\
                .should.equal(Just(target))

    def add_remove_project(self):
        ctx = self._prot(List(), List(self.project_base), self.type_bases)
        with ctx as prot:
            prot.send_sync(AddByParams(self.pypro1_name, {}))\
                .project(self.pypro1_name)\
                .map(_.root)\
                .should.contain(self.pypro1_root)
            prot.send_sync(RemoveByIdent(self.pypro1_name))\
                .all_projects.should.be.empty

    def add_by_params(self):
        tpe = 'ptype'
        name = 'pname'
        root = temp_dir('proteome/add_by_params')
        params = Map(
            type=tpe,
            root=root
        )
        with self._prot() as prot:
            ret = prot.send_sync(AddByParams(name, params))
            (ret.project(name) / _.root).should.contain(root)

__all__ = ('Proteome_',)
