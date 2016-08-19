from proteome.project import Project
from ribosome import ProcessExecutor, Job


class Ctags(ProcessExecutor):  # type: ignore

    def gen(self, project: Project):
        langs = ','.join(project.ctags_langs)
        tag_file = project.tag_file
        args = [
            '-R',
            '--languages={}'.format(langs),
            '-f',
            str(tag_file),
            str(project.root)
        ]
        job = Job(
            client=project.job_client,
            exe='ctags',
            args=args,
            loop=self.loop)
        return self.run(job)

__all__ = ('Ctags',)
