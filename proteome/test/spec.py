from pathlib import Path

from tryp.test import temp_dir  # type: ignore

import tryp.test
from tryp import Just

from proteome.project import Project  # type: ignore


class Spec(tryp.test.Spec):

    def setup(self):
        super().setup()
        self.temp_projects = Path(temp_dir('projects'))
        self.history_base = Path(temp_dir('history'))

    def mk_project(self, name, tpe):
        root = temp_dir(str(self.temp_projects / tpe / name))
        return Project.of(name, Path(root), tpe=Just(tpe))

    def object_files(self, pro: Project):
        objdir = self.history_base / pro.fqn / 'objects'
        return list((objdir).iterdir())

__all__ = ('Spec',)
