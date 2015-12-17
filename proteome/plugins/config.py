from fn import F, _  # type: ignore

from trypnv.machine import may_handle

from proteome.state import ProteomeComponent
from proteome.env import Env
from proteome.plugins.core import CurrentAdded, Ready


class Plugin(ProteomeComponent):

    def _runtime(self, project, base):
        run = F(self.vim.runtime) << F('{}/{}'.format, base)
        project.all_types.foreach(run)
        project.tpe.map(_ + '/' + project.name).foreach(run)
        run('all/*.vim')

    def _runtime_before(self, project):
        return self._runtime(project, 'project')

    def _runtime_after(self, project):
        return self._runtime(project, 'project_after')

    @may_handle(CurrentAdded)
    def stage1(self, env: Env, msg):
        env.current.foreach(self._runtime_before)

    @may_handle(Ready)
    def stage2(self, env: Env, msg):
        env.current.foreach(self._runtime_after)

__all__ = ('Plugin')
