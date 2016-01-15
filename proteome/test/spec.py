from typing import Callable, Any
from contextlib import contextmanager
from pathlib import Path

from flexmock import flexmock  # type: ignore

from tek.test import temp_dir

import tryp
import tryp.test
from tryp import may, Maybe, Just
from tryp.logging import tryp_stdout_logging

from proteome.nvim import NvimFacade
from proteome.project import Project

from trypnv.nvim import Buffer


class MockNvimFacade(NvimFacade):

    def __init__(self):
        self.vars = {}
        super(MockNvimFacade, self).__init__(None)
        self.target = self

    @may
    def var(self, name: str) -> Maybe[str]:  # type: ignore
        v = self.vars.get(name)
        if v is None:
            self.log.error('variable not found: {}'.format(name))
        return v

    @property
    def current_buffer(self):
        return Buffer(self, self, self.prefix)

    def switch_root(self, root):
        pass

    def async(self, f: Callable[['NvimFacade'], Any]):
        return f(self)

    @contextmanager
    def main_event_loop(self):
        yield

    def cmd(self, *a, **kw):
        pass


class Spec(tryp.test.Spec):

    def setup(self, *a, **kw):
        tryp.development = True
        tryp_stdout_logging()
        super(Spec, self).setup(*a, **kw)
        self.temp_projects = Path(temp_dir('projects'))
        self.history_base = Path(temp_dir('history'))

    def mk_project(self, name, tpe):
        root = temp_dir(str(self.temp_projects / tpe / name))
        return Project.of(name, Path(root), tpe=Just(tpe))

    def object_files(self, pro: Project):
        objdir = self.history_base / pro.fqn / 'objects'
        return list((objdir).iterdir())


class MockNvimSpec(Spec):

    def setup(self, *a, **kw):
        super(MockNvimSpec, self).setup(*a, **kw)
        self.vim = MockNvimFacade()
        self.vim_mock = flexmock(self.vim)

__all__ = ['Spec']
