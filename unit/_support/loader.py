from pathlib import Path

from tryp.test import fixture_path, temp_dir

from tryp import List, Map

from proteome.project import Resolver, ProjectLoader

from unit._support.spec import UnitSpec


class LoaderSpec(UnitSpec):

    def mk_project_root(self, tpe, name, base=None):
        base = base or self.project_base
        root = temp_dir(str(base / tpe / name))
        root.mkdir(parents=True, exist_ok=True)
        return Path(root)

    def setup(self):
        super().setup()
        self.pypro1_type = 'python'
        self.pypro1_name = 'pypro1'
        self.pypro2_name = 'pypro2'
        self.config = Path(fixture_path('conf'))
        self.project_base = Path(temp_dir('projects'))
        self.project_base2 = Path(temp_dir('projects2'))
        self.pypro1_root = self.mk_project_root(self.pypro1_type,
                                                self.pypro1_name)
        self.mk_project_root(self.pypro1_type, self.pypro2_name,
                             self.project_base2)
        self.mk_project_root('other', 'other2', self.project_base2)
        self.type1_base = Path(temp_dir('type1_projects'))
        self.type1pro_name = 'type1pro'
        self.type1pro_root = temp_dir(self.type1_base / self.type1pro_name)
        self.type_bases = Map({self.type1_base: List('type1')})
        self.resolver = Resolver(List(self.project_base, self.project_base2),
                                 self.type_bases)
        self.loader = ProjectLoader(self.config, self.resolver)

__all__ = ('LoaderSpec',)
