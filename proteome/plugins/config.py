from fn import F, _

from ribosome.machine import may_handle

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.plugins.core import MainAdded, StageIII


class Plugin(ProteomeComponent):

    class Transitions(ProteomeTransitions):

        @property
        def _project_dir(self):
            return self.vim.vars.p('config_project_dir')\
                .get_or_else('project')

        @property
        def _project_after_dir(self):
            return self.vim.vars.p('config_project_after_dir')\
                .get_or_else('project_after')

        def _runtime(self, project, base):
            run = F(self.vim.runtime) << F('{}/{}'.format, base)
            project.all_types.foreach(run)
            project.tpe.map(_ + '/' + project.name).foreach(run)
            run('all/*')

        def _runtime_before(self, project):
            return self._runtime(project, self._project_dir)

        def _runtime_after(self, project):
            return self._runtime(project, self._project_after_dir)

        @may_handle(MainAdded)
        def before(self):
            self.data.current.foreach(self._runtime_before)

        @may_handle(StageIII)
        def stage_3(self):
            self.data.current.foreach(self._runtime_after)

__all__ = ('Plugin',)
