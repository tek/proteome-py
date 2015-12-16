from pathlib import Path
from typing import Callable, Any
from datetime import datetime

from tryp import _
from tryp.lazy import lazy

from trypnv.machine import may_handle, message

from proteome.state import ProteomeComponent
from proteome.env import Env
from proteome.git import HistoryGit
from proteome.project import Project
from proteome.plugins.core import Ready, Save

Commit = message('Commit')


class Plugin(ProteomeComponent):

    @lazy
    def git(self):
        base = self.vim.pdir('history_base').get_or_else(Path('/dev/null'))
        return HistoryGit(base, self.vim)

    def _commit(self, pro: Project):
        self.log.debug('commiting to history repo for {}'.format(pro))
        return self.git.add_commit_all(pro, datetime.now().isoformat())

    def _init(self, pro: Project):
        self.log.debug('initializing history repo for {}'.format(pro))
        return self.git.init(pro)

    @property
    def all_projects_history(self):
        return self.pflags.all_projects_history

    @property
    def git_ready(self):
        return self.git is not None and self.git.ready

    def _handle(self, env: Env, handler: Callable[[Project], Any]):
        name = handler.__name__
        if self.git_ready:
            projects = env.all_projects
            if not self.all_projects_history:
                projects = projects.filter(_.history)
            inf = 'running history handler {} on {}'
            self.log.verbose(inf.format(name, projects))
            projects.map(handler)
            self.git.exec()
        else:
            err = 'tried to run {} on history while not ready'
            self.log.verbose(err.format(name))

    @may_handle(Ready)
    def ready(self, env: Env, msg):
        self._handle(env, self._init)

    @may_handle(Commit)
    def commit(self, env: Env, msg):
        self._handle(env, self._commit)

    @may_handle(Save)
    def save(self, env, msg):
        self.commit(env, msg)

__all__ = ['Commit', 'Plugin']
