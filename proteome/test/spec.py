from pathlib import Path

from amino.test import temp_dir

from amino import Just

from proteome.project import Project


class Spec:

    def setup(self):
        self.temp_projects = Path(temp_dir('projects'))
        self.history_base = Path(temp_dir('history'))

    def mk_project(self, name, tpe):
        root = temp_dir(str(self.temp_projects / tpe / name))
        return Project.of(name, Path(root), tpe=Just(tpe))

    def object_files(self, pro: Project):
        objdir = self.history_base / pro.fqn / 'objects'
        return list((objdir).iterdir())

__all__ = ('Spec',)
