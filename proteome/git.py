from pathlib import Path

from proteome.project import Project
from proteome.process import ProcessExecutor, Job  # type: ignore


class Git(ProcessExecutor):

    def pre_args(self, project: Project):
        return []

    def command(self, project: Project, name: str, *cmd_args):
        args = self.pre_args(project) + [name] + list(cmd_args)
        self.log.debug('running git {}'.format(' '.join(args)))
        return self.run(Job(project, 'git', args))

    # TODO remove dangling lock file
    # and set the excludesfile
    def init(self, project: Project):
        return self.command(project, 'init')

    def add_commit_all(self, project: Project, message: str):
        return self.command(project, 'add', '-A', str(project.root))\
            .flat_map(lambda a: self.command(project, 'commit', '-m', message))


class HistoryGit(Git):

    def __init__(self, base: Path) -> None:
        self.base = base
        super(HistoryGit, self).__init__()

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

    @property
    def ready(self):
        return self.base.is_dir() and super(HistoryGit, self).ready

__all__ = ['Git']
