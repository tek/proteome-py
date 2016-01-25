from pathlib import Path

from tryp.test import fixture_path, temp_dir  # type: ignore

from tryp import List, Map

from proteome.project import Resolver, ProjectLoader

from unit._support.spec import UnitSpec


class LoaderSpec(UnitSpec):

    def setup(self):
        super().setup()
        self.pypro1_name = 'pypro1'
        self.config = Path(fixture_path('conf'))
        self.project_base = Path(temp_dir('projects'))
        self.pypro1_type = 'python'
        self.pypro1_root = (self.project_base / self.pypro1_type /
                            self.pypro1_name)
        self.pypro1_root.mkdir(parents=True, exist_ok=True)
        self.type1_base = Path(fixture_path('type1_projects'))
        self.type1pro_name = 'type1pro'
        self.type_bases = Map({self.type1_base: List('type1')})
        self.resolver = Resolver(List(self.project_base),
                                 self.type_bases)
        self.loader = ProjectLoader(self.config, self.resolver)

__all__ = ['LoaderSpec']
