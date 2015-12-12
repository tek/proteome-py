from pathlib import Path

from proteome.project import (Projects, Resolver, ProjectLoader, Project,
                              ProjectAnalyzer)
from proteome.nvim import NvimFacade
from trypnv.machine import Data

from tryp import List, Map, Just

import pyrsistent  # type: ignore


def field(tpe, **kw):
    return pyrsistent.field(type=tpe, mandatory=True, **kw)


class Env(pyrsistent.PRecord, Data):
    config_path = field(Path)
    bases = field(List)
    type_bases = field(Map)
    projects = field(Projects)
    current_index = field(int, initial=0)
    initialized = field(bool, initial=False)

    @property
    def loader(self):
        return ProjectLoader(self.config_path, self.resolver)

    @property
    def resolver(self):
        return Resolver(self.bases, self.type_bases)

    def __str__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            self.projects
        )

    @property
    def current(self):
        return self.projects[self.current_index]

    @property
    def project_count(self):
        return len(self.projects)

    def inc(self, num):
        new_index = (self.current_index + num) % self.project_count
        return self.set_index(new_index)

    def set_index(self, index):
        return self.set(current_index=index)

    def add(self, pro: Project):
        return self if pro in self else self.set(projects=self.projects + pro)

    def __add__(self, pro: Project):
        return self.add(pro)

    def remove(self, ident):
        pro = (Just(ident) if isinstance(ident, Project) else
               self.project(ident))
        return pro\
            .cata(lambda p: self.set(projects=self.projects - p), self)

    def __sub__(self, ident):
        return self.remove(ident)

    def analyzer(self, vim: NvimFacade):
        return ProjectAnalyzer(vim, self.loader)

    def project(self, ident: str):
        return self.projects.project(ident)

    @property
    def all_projects(self):
        return self.projects.projects

    def __contains__(self, item):
        return item in self.projects

__all__ = ['Env']
