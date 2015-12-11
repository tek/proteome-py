from pathlib import Path

from proteome.project import (Projects, Resolver, ProjectLoader, Project,
                              ProjectAnalyzer)
from proteome.nvim import NvimFacade

from tryp import List, Map

import pyrsistent  # type: ignore


def field(tpe, **kw):
    return pyrsistent.field(type=tpe, mandatory=True, **kw)


class Env(pyrsistent.PRecord):
    config_path = field(Path)
    bases = field(List)
    type_bases = field(Map)
    projects = field(Projects)
    current_index = field(int, initial=0)

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
        return self.set(current_index=new_index)

    def add(self, pro: Project):
        return self if pro in self else self.set(projects=self.projects + pro)

    def __add__(self, pro: Project):
        return self.add(pro)

    def remove(self, ident: str):
        return self.project(ident)\
            .cata(lambda pro: self.set(projects=self.projects - pro), self)

    def __sub__(self, ident: str):
        return self.remove(ident)

    def analyzer(self, vim: NvimFacade):
        return ProjectAnalyzer(vim, self.loader)

    def project(self, ident: str):
        return self.projects.project(ident)

    @property
    def all_projects(self):
        return self.projects.projects

__all__ = ['Env']
