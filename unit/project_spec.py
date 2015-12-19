from pathlib import Path

import sure  # NOQA
from flexmock import flexmock  # NOQA
from pathlib import Path

from fn import _  # type: ignore

from tek.test import temp_dir

from tryp import Just, List, Empty, Map

from proteome.project import Project, Projects
from proteome.logging import Logging
from proteome.test.spec import MockNvimSpec

from unit._support.loader import _LoaderSpec


class Projects_(_LoaderSpec):

    def setup(self, *a, **kw):
        super(Projects_, self).setup(*a, **kw)

    def show(self):
        n = 'some name'
        d = Path('/dir/to/project')
        p2 = Projects() + Project.of(n, d)
        p2.show().should.equal(List('{}: {}'.format(n, d)))
        p2.show(List(n)).should.equal(List('{}: {}'.format(n, d)))
        str(p2).should.equal("Projects(Project('{}'))".format(n))

    def remove(self):
        n = 'some name'
        d = '/dir/to/project'
        t = 'sometype'
        p2 = Projects() + Project.of(n, Path(d), Just(t))
        pro = p2.project('{}/{}'.format(t, n))
        pro.map(_.root).should.equal(Just(Path(d)))
        (p2 - pro._get).projects.should.be.empty


class ProjectLoader_(_LoaderSpec):

    def setup(self, *a, **kw):
        super(ProjectLoader_, self).setup(*a, **kw)

    def resolve(self):
        type_name = '{}/{}'.format(self.pypro1_type, self.pypro1_name)
        split = self.loader\
            .resolve(self.pypro1_type, self.pypro1_name)
        split\
            .map(_.root)\
            .should.equal(Just(self.pypro1_root))
        self.loader\
            .resolve_ident(type_name)\
            .should.equal(split)

    def config(self):
        self.loader.config.lift(0)\
            .flat_map(lambda a: a.get('name'))\
            .should.equal(Just(self.pypro1_name))

    def json_by_name(self):
        self.loader.json_by_ident(self.pypro1_name)\
            .flat_map(lambda a: a.get('type'))\
            .should.equal(Just(self.pypro1_type))
        self.loader.json_by_name(self.pypro1_name)\
            .flat_map(lambda a: a.get('type'))\
            .should.equal(Just(self.pypro1_type))
        self.loader.by_ident(self.pypro1_name)\
            .flat_map(_.tpe)\
            .should.equal(Just(self.pypro1_type))

    def json_by_type_name(self):
        type_name = '{}/{}'.format(self.pypro1_type, self.pypro1_name)
        self.loader.json_by_ident(type_name)\
            .flat_map(lambda a: a.get('type'))\
            .should.equal(Just(self.pypro1_type))
        self.loader.by_ident(type_name)\
            .flat_map(_.tpe)\
            .should.equal(Just(self.pypro1_type))
        self.loader.by_ident('invalid')\
            .should.equal(Empty())

    def from_file(self):
        pj = self.loader.by_ident(self.pypro1_name)
        pj.should.be.a(Just)
        pro = pj._get
        pro.should.be.a(Project)
        pro.name.should.equal(self.pypro1_name)
        pro.tpe.should.equal(Just(self.pypro1_type))

    def from_params(self):
        tpe = 'ptype'
        name = 'pname'
        ident = '{}/{}'.format(tpe, name)
        root = temp_dir('loader/from_params')
        types = ['a', 'b']
        langs = ['c', 'd']
        params = Map(
            types=types,
            langs=langs,
            history=False,
        )
        pro = self.loader.from_params(ident, root, params)
        pro.should.contain(Project.of(name, root, Just(tpe)))
        pro.x.types.should.equal(types)
        pro.x.langs.should.equal(langs)
        pro.x.history.should_not.be.ok

    def from_params_no_type(self):
        name = 'pname'
        root = temp_dir('loader/from_params')
        pro = self.loader.from_params(name, root, Map())
        pro.should.contain(Project.of(name, root, Empty()))


class ProjectResolver_(_LoaderSpec, MockNvimSpec, Logging):

    def setup(self, *a, **kw):
        super(ProjectResolver_, self).setup(*a, **kw)

    def in_base(self):
        p = self.pypro1_root
        self.resolver.dir(p).should.equal(
            Just((self.pypro1_type, self.pypro1_name)))
        p = self.type1_base / self.type1pro_name
        self.resolver.dir(p).should.equal(
            Just(('type1', self.type1pro_name)))

__all__ = ['Projects_', 'ProjectLoader_']
