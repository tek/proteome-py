from pathlib import Path

import sure  # NOQA
from flexmock import flexmock  # NOQA

from proteome.nvim_plugin import Create
from proteome.project import Project, Projects, ProjectAnalyzer
from proteome.plugins.core import Next, Prev, Init, AddByIdent, RemoveByIdent
from proteome.main import Proteome

from tryp import List, Just, _, Map

from unit._support.spec import MockNvimSpec
from unit._support.loader import _LoaderSpec
from unit._support.async import test_loop

from tek.test import temp_dir


class Proteome_(MockNvimSpec, _LoaderSpec):

    def create(self):
        name = 'proj'
        root = Path('/dev/null')
        prot = Proteome(self.vim, root, List(), List(), Map())
        prot.send(Create(name, root))
        p = prot._data.projects.projects[0]
        p.name.should.equal(name)
        p.root.should.equal(root)

    def cycle(self):
        self.vim_mock.should_receive('switch_root').and_return(None)
        name = 'proj'
        name2 = 'proj2'
        root = Path('/dev/null')
        prot = Proteome(self.vim, root, List(), List(), Map())
        pros = List(Project(name, root), Project(name2, root))
        prot._data = prot._data.set(projects=Projects(pros))
        prot._data.current.should.equal(Just(pros[0]))
        prot.send(Next())
        prot._data.current.should.equal(Just(pros[1]))
        prot.send(Prev())
        prot._data.current.should.equal(Just(pros[0]))

    def command(self):
        class P(Proteome):
            def init(self):
                return dict()
        plug = 'unit._support.test_plug'
        prot = P(self.vim, Path('/dev/null'), List(plug), List(), Map())
        data = 'message_data'
        prot.plug_command('test_plug', 'do', [data])
        prot._data.should.have.key(data).being.equal(data)

    def invalid_command(self):
        class P(Proteome):
            def init(self):
                return dict()
        plug = 'unit._support.test_plug'
        prot = P(self.vim, Path('/dev/null'), List(plug), List(), Map())
        data = 'message_data'
        prot.plug_command('test_plug', 'do', [data])
        prot.plug_command('test_plug', 'dont', [data])
        prot._data.should.have.key(data).being.equal(data)

    def ctags(self):
        plug_name = 'proteome.plugins.ctags'
        p1 = self.mk_project('pro1', 'c')
        p2 = self.mk_project('pro2', 'go')
        prot = Proteome(self.vim, Path('/dev/null'), List(plug_name), List(),
                        Map())
        plug = prot.plugin('ctags')._get
        pros = List(p1, p2)
        prot._data = prot._data.set(projects=Projects(pros))
        p1.tag_file.exists().should_not.be.ok
        p2.tag_file.exists().should_not.be.ok
        with test_loop():
            prot.plug_command('ctags', 'gen', List())
            plug.ctags.exec_pending()
        plug.ctags.current.keys.should.be.empty
        p1.tag_file.exists().should.be.ok
        p2.tag_file.exists().should.be.ok

    def history(self):
        history_base = temp_dir('proteome', 'history')
        self.vim.vars['proteome_history_base'] = str(history_base)
        plug_name = 'proteome.plugins.history'
        p1 = self.mk_project('pro1', 'c')
        p2 = self.mk_project('pro2', 'go')
        prot = Proteome(self.vim, Path('/dev/null'), List(plug_name), List(),
                        Map())
        plug = prot.plugin('history')._get
        pros = List(p1, p2)
        prot._data = prot._data.set(projects=Projects(pros))
        with test_loop():
            prot.plug_command('history', 'ready', List())
            plug.git.exec_pending()
        plug.git.current.keys.should.be.empty
        (history_base / p1.fqn / 'HEAD').exists().should.be.ok
        (history_base / p2.fqn / 'HEAD').exists().should.be.ok

    def current_project(self):
        p = self.pypro1_root
        flexmock(ProjectAnalyzer).should_receive('current_dir').and_return(p)
        prot = Proteome(self.vim, Path('/dev/null'), List(),
                        List(self.project_base), self.type_bases)
        prot.send(Init())
        prot._data.projects.projects.head.should.equal(
            Just(Project(self.pypro1_name, p, Just(self.pypro1_type)))
        )

    def add_remove_project(self):
        prot = Proteome(self.vim, self.config, List(),
                        List(self.project_base), self.type_bases)
        prot.send(AddByIdent(self.pypro1_name))
        prot._data.project(self.pypro1_name)\
            .map(_.root)\
            .should.equal(Just(self.pypro1_root))
        prot.send(RemoveByIdent(self.pypro1_name))
        prot._data.all_projects.should.be.empty

__all__ = ['Proteome_']
