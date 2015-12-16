from pathlib import Path

import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List, Just, _, Map

import trypnv
from trypnv.machine import Nop

from proteome.nvim_plugin import Create
from proteome.project import Project, Projects, ProjectAnalyzer
from proteome.plugins.core import Next, Prev, Init, AddByIdent, RemoveByIdent
from proteome.main import Proteome
from proteome.test.spec import MockNvimSpec

from unit._support.loader import _LoaderSpec
from unit._support.async import test_loop

from tek.test import temp_dir

null = Path('/dev/null')


class DictProteome(Proteome):
    _data_type = dict

    def init(self):
        return dict()


class Proteome_(MockNvimSpec, _LoaderSpec):

    def _prot(self, *a):
        trypnv.in_vim = False
        return Proteome(self.vim, self.config, *a).transient()

    def create(self):
        name = 'proj'
        with self._prot(List(), List(), Map()) as prot:
            data = prot.send_wait(Create(name, null))
        p = data.projects.projects[0]
        p.name.should.equal(name)
        p.root.should.equal(null)

    def cycle(self):
        self.vim_mock.should_receive('switch_root').and_return(None)
        name = 'proj'
        name2 = 'proj2'
        with self._prot(List(), List(), Map()) as prot:
            pros = List(Project(name, null), Project(name2, null))
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
        with self._prot(List(plug_name), List(), Map()) as prot:
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

    def history(self):
        history_base = temp_dir('proteome', 'history')
        self.vim.vars['proteome_history_base'] = str(history_base)
        plug_name = 'proteome.plugins.history'
        p1 = self.mk_project('pro1', 'c')
        p2 = self.mk_project('pro2', 'go')
        with self._prot(List(plug_name), List(), Map()) as prot:
            plug = prot.plugin('history')._get
            pros = List(p1, p2)
            prot.data = prot.data.set(projects=Projects(pros))
            prot.plug_command('history', 'ready', List())
            with test_loop() as loop:
                plug.git.await_threadsafe(loop)
            plug.git.current.keys.should.be.empty
        (history_base / p1.fqn / 'HEAD').exists().should.be.ok
        (history_base / p2.fqn / 'HEAD').exists().should.be.ok

    def current_project(self):
        p = self.pypro1_root
        flexmock(ProjectAnalyzer).should_receive('current_dir').and_return(p)
        ctx = self._prot(List(), List(self.project_base), self.type_bases)
        target = Project(self.pypro1_name, p, Just(self.pypro1_type))
        with ctx as prot:
            prot.send_wait(Init())
            prot.send_wait(Nop())\
                .projects.projects.head\
                .should.equal(Just(target))

    def add_remove_project(self):
        ctx = self._prot(List(), List(self.project_base), self.type_bases)
        with ctx as prot:
            prot.send_wait(AddByIdent(self.pypro1_name))\
                .project(self.pypro1_name)\
                .map(_.root)\
                .should.equal(Just(self.pypro1_root))
            prot.send_wait(RemoveByIdent(self.pypro1_name))\
                .all_projects.should.be.empty

__all__ = ['Proteome_']
