from pathlib import Path
import tempfile

from fn import _

from proteome.project import (Projects, Resolver, ProjectLoader, Project,
                              ProjectAnalyzer)
from proteome.logging import Logging
from ribosome.data import Data
from ribosome.record import field
from ribosome import NvimFacade

from amino import List, Map, Just, Boolean


class Env(Data, Logging):
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
        return '{}({},{},{})'.format(
            self.__class__.__name__,
            self.current_index,
            self.initialized,
            self.projects,
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

    def set_index_by_ident(self, ident):
        return self.projects.index_of_ident(ident)\
            .map(self.set_index)

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

    @property
    def main(self):
        return self.projects[0]

    def history_projects(self, all_projects: bool):
        want_history = _.history
        filter = ((lambda a: want_history(a) or a.has_type)
                  if all_projects
                  else want_history)
        return self.all_projects.filter(filter)

    @property
    def main_type(self):
        return self.main.flat_map(_.tpe)

    @property
    def addable(self):
        return self.loader.all_ident(self.main_type)

    @property
    def main_addable(self):
        return self.loader.main_ident(self.main_type)

    @property
    def main_clone_dir(self):
        temp = lambda: tempfile.mkdtemp(prefix='proteome_clone')
        return self.resolver.bases.head\
            .ap2(self.main_type, _ / _)\
            .or_else(temp)

    def is_ident_current(self, ident):
        return Boolean(
            self.projects.index_of_ident(ident).contains(self.current_index))

__all__ = ['Env']
