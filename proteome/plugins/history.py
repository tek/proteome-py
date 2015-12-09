from pathlib import Path
from typing import Callable, Any
from datetime import datetime

from tryp import _

from trypnv.machine import may_handle, message
from trypnv import Log

from proteome.state import ProteomeComponent
from proteome.env import Env
from proteome.git import HistoryGit
from proteome.project import Project
from proteome.plugins.core import Init

Commit = message('Commit')


class Plugin(ProteomeComponent):

    def __init__(self, *a, **kw):
        super(Plugin, self).__init__(*a, **kw)
        var = self.vim.pvar('history_base')
        base = var.map(lambda a: Path(a))\
            .filter(lambda a: a.is_dir())
        if not base.isJust:
            msg = 'g:proteome_history_base is not a directory ({})'
            Log.error(msg.format(var))
        self.git = HistoryGit(base.get_or_else('/dev/null'))

    def _commit(self, pro: Project):
        return self.git.commit_all(pro, datetime.now().isoformat())

    def _init(self, pro: Project):
        return self.git.init(pro)

    def _handle(self, env: Env, handler: Callable[[Project], Any]):
        if self.git.ready:
            env.projects.projects\
                .filter(_.history)\
                .map(handler)

    @may_handle(Init)
    def init(self, env: Env, msg):
        self._handle(env, self._init)

    @may_handle(Commit)
    def commit(self, env: Env, msg):
        self._handle(env, self._commit)

__all__ = ['Commit', 'Plugin']
