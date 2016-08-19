from ribosome import ProcessExecutor, Job

from proteome.project import Project
from proteome.git.repo import CommitInfo


class Git(ProcessExecutor):

    def pre_args(self, project: Project):
        return []

    def command(self, client, git_args, name, *cmd_args):
        args = list(map(str, git_args + [name] + list(cmd_args)))
        self.log.debug('running git {}'.format(' '.join(args)))
        job = Job(
            client=client,
            exe='git',
            args=args,
            loop=self.loop,
        )
        return self.run(job)

    def project_command(self, project: Project, name: str, *cmd_args):
        return self.command(project.job_client, self.pre_args(project), name,
                            *cmd_args)

    def revert(self, project: Project, commit: CommitInfo):
        return self.project_command(project, 'revert', '-n', commit.hex)

    def revert_abort(self, project: Project):
        return self.project_command(project, 'revert', '--abort')

    def clone(self, client, url, location):
        self.log.info('Cloning {}...'.format(url))
        return self.command(client, [], 'clone', url, location)

    def add_all(self, project: Project):
        return self.project_command(project, 'add', '-A', '.')

    def commit(self, project: Project, msg: str):
        return self.project_command(project, 'commit', '-m', msg)

__all__ = ('Git',)
