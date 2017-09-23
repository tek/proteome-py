from amino import Path

from proteome.project import Project
from proteome.git import Git


class HistoryGit(Git):

    def __init__(self, base: Path, vim) -> None:
        self.base = base
        super(HistoryGit, self).__init__(vim)

    def pre_args(self, project: Project):
        d = str(project.root)
        h = str(self._history_dir(project))
        return [
            '--git-dir',
            h,
            '--work-tree',
            d,
        ]

    def _history_dir(self, project: Project):
        return self.base / project.fqn

__all__ = ('HistoryGit',)
