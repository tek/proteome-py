from pathlib import Path

from tek.test import fixture_path, temp_dir  # type: ignore

from tryp import List, Map, Just

from integration._support.spec import Spec

from proteome.project import Project

class IntegrationSpec(Spec):

    def setup(self, *a, **kw):
        super(IntegrationSpec, self).setup(*a, **kw)
        self.config = fixture_path('conf')
        self.base = temp_dir('projects', 'base')
        self.type1_base = temp_dir('projects', 'type1')
        self.type_bases = Map({self.type1_base: List('type1')})
        self.history_base = temp_dir('history')

    def mk_project(self, tpe, name):
        root = temp_dir(str(self.base / tpe / name))
        return Project(name, Path(root), tpe=Just(tpe))

    def add_projects(self, *pros):
        return List(*pros).smap(self.mk_project)

__all__ = ['IntegrationSpec']
