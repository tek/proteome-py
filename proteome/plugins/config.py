from ribosome.machine import handle
from ribosome.machine.transition import Error

from amino import List, L, _

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
            ''' first runtimes all project type files, like
            `project/type.vim`, then the specific project file, like
            `project/type/name.vim`.
            '''
            def run(path_suf):
                path = '{}/{}'.format(base, path_suf)
                err = 'error sourcing {}.vim: {{}}'.format(path)
                return (
                    self.vim.runtime(path)
                    .cata(L(err.format)(_.cause) >> List, lambda a: List())
                )
            return (
                project.all_types.flat_map(run) +
                (project.tpe.map(_ + '/' + project.name).map(run) | List()) +
                run('all/*')
            ).map(Error)

        def _runtime_before(self, project):
            return self._runtime(project, self._project_dir)

        def _runtime_after(self, project):
            return self._runtime(project, self._project_after_dir)

        @handle(MainAdded)
        def before(self):
            return self.data.current.map(self._runtime_before)

        @handle(StageIII)
        def stage_3(self):
            return self.data.current.map(self._runtime_after)

__all__ = ('Plugin',)
