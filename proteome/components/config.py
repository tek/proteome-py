from ribosome.machine.transition import handle
from ribosome.machine.messages import Error

from amino import List, L, _

from ribosome.machine.messages import Stage2, Stage3
from ribosome.machine.state import Component


class Config(Component):

    @property
    def _project_dir(self):
        return self.vim.vars.p('config_project_dir') | 'project'

    @property
    def _project_after_dir(self):
        return self.vim.vars.p('config_project_after_dir') | 'project_after'

    def _runtime(self, project, base):
        ''' first runtimes all project type files, like `project/type.vim`, then the specific project file, like
        `project/type/name.vim`.
        '''
        def run(path_suf):
            path = '{}/{}'.format(base, path_suf)
            err = 'error sourcing {}.vim: {{}}'.format(path)
            return (
                self.vim.runtime(path)
                .cata(L(err.format)(_) >> List, lambda a: List())
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

    @handle(Stage2)
    def before(self):
        return self.data.current.map(self._runtime_before)

    @handle(Stage3)
    def stage_3(self):
        return self.data.current.map(self._runtime_after)

__all__ = ('Config',)
