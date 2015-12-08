from tryp import _

from trypnv.machine import may_handle, message

from proteome.state import ProteomeComponent
from proteome.env import Env
from proteome.git import GitExecutor
from proteome.project import Project

Commit = message('Commit')


class Plugin(ProteomeComponent):

    git = GitExecutor()

    def _commit(self, pro: Project):
        return self.git.run(pro)

    @may_handle(Init)
    def commit(self, env: Env, msg):
        pass

    @may_handle(Commit)
    def commit(self, env: Env, msg):
        if self.git.ready:
            env.projects.projects\
                .filter(_.want_history)\
                .map(self._commit)

__all__ = ['Commit', 'Plugin']
