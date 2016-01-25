from pathlib import Path

import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List, Just, _, Map

import trypnv
from trypnv.machine import Nop

from proteome.nvim_plugin import Create
from proteome.project import Project, Projects, ProjectAnalyzer
from proteome.plugins.core import (Next, Prev, StageI, AddByParams,
                                   RemoveByIdent)
from proteome.main import Proteome

from unit._support.loader import LoaderSpec
from unit._support.async import test_loop

from tryp.test import temp_dir, later

null = Path('/dev/null')


class DictProteome(Proteome):
    _data_type = dict

    def init(self):
        return dict()


class Proteome_(LoaderSpec):

    def _prot(self, p=List(), b=List(), t=Map()):
        trypnv.in_vim = False
        return Proteome(self.vim, self.config, p, b, t).transient()

    def create(self):
        name = 'proj'
        with self._prot() as prot:
            data = prot.send_wait(Create(name, null))
        p = data.projects.projects[0]
        p.name.should.equal(name)
        p.root.should.equal(null)

    def cycle(self):
        self.vim_mock.should_receive('switch_root').and_return(None)
        name = 'proj'
        name2 = 'proj2'
        with self._prot() as prot:
            pros = List(Project.of(name, null), Project.of(name2, null))
            prot.data = prot.data.set(projects=Projects(pros))
            prot.data.current.should.equal(Just(pros[0]))
            prot.send_wait(Next())\
                .current.should.equal(Just(pros[1]))
            prot.send_wait(Prev())\
                .current.should.equal(Just(pros[0]))

    def command(self):
        plug = 'unit._support.test_plug'
        prot = DictProteome(self.vim, null, List(plug), List(), Map())
        data = 'message_data'
        prot.plug_command('test_plug', 'do', [data])
        prot.data.should.have.key(data).being.equal(data)

    def invalid_command(self):
        plug = 'unit._support.test_plug'
        prot = DictProteome(self.vim, null, List(plug), List(), Map())
        data = 'message_data'
        prot.plug_command('test_plug', 'do', [data])
        prot.plug_command('test_plug', 'dont', [data])
        prot.data.should.have.key(data).being.equal(data)

    def ctags(self):
        plug_name = 'proteome.plugins.ctags'
        p1 = self.mk_project('pro1', 'c')
        p2 = self.mk_project('pro2', 'go')
        with self._prot(List(plug_name)) as prot:
            plug = prot.plugin('ctags')._get
            pros = List(p1, p2)
            prot.data = prot.data.set(projects=Projects(pros))
            p1.tag_file.exists().should_not.be.ok
            p2.tag_file.exists().should_not.be.ok
            prot.plug_command('ctags', 'gen', List())
            with test_loop() as loop:
                plug.ctags.await_threadsafe(loop)
            plug.ctags.current.keys.should.be.empty
            p1.tag_file.exists().should.be.ok
            p2.tag_file.exists().should.be.ok

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

        def _three_commits(self, prot):
            pros = List(self.main_project)
            prot.data = prot.data.set(projects=Projects(pros))
            for cont in self.test_content:
                self.test_file_1.write_text(cont)
                prot.plug_command('history', 'Commit', List())

        def history(self):
            p1 = self.main_project
            p2 = self.mk_project('pro2', 'go')
            with self._prot(List(self.plug_name)) as prot:
                pros = List(p1, p2)
                prot.data = prot.data.set(projects=Projects(pros))
                prot.plug_command('history', 'StageIV', List())
                (self.history_base / p1.fqn / 'HEAD').exists().should.be.ok
                (self.history_base / p2.fqn / 'HEAD').exists().should.be.ok
                self._three_commits(prot)
                prot.plug_command('history', 'HistoryLog', List())
                prot.plug_command('history', 'HistoryPrev', List())
                self.test_file_1.read_text().should.equal(self.test_content[1])
                prot.plug_command('history', 'HistoryNext', List())
                self.test_file_1.read_text().should.equal(self.test_content[2])

        def browse(self):
            with self._prot(List(self.plug_name)) as prot:
                self._three_commits(prot)
                prot.plug_command('history', 'HistoryBrowse')

    def current_project(self):
        p = self.pypro1_root
        flexmock(ProjectAnalyzer).should_receive('main_dir').and_return(p)
        ctx = self._prot(b=List(self.project_base), t=self.type_bases)
        target = Project.of(self.pypro1_name, p, Just(self.pypro1_type))
        with ctx as prot:
            prot.send_wait(StageI())
            prot.send_wait(Nop())\
                .projects.projects.head\
                .should.equal(Just(target))

    def add_remove_project(self):
        ctx = self._prot(List(), List(self.project_base), self.type_bases)
        with ctx as prot:
            prot.send_wait(AddByParams(self.pypro1_name, {}))\
                .project(self.pypro1_name)\
                .map(_.root)\
                .should.contain(self.pypro1_root)
            prot.send_wait(RemoveByIdent(self.pypro1_name))\
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
            prot.send_wait(AddByParams(name, params))\
                .project(name)\
                .map(_.root)\
                .should.contain(root)

__all__ = ['Proteome_']
