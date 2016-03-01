from proteome.project import Project
from trypnv import ProcessExecutor, Job  # type: ignore

from tryp import Just


class Patch(ProcessExecutor):  # type: ignore

    def patch(self, project: Project, diff: str):
        args = ['-p1', '-r-']
        job = Job(
            client=project.job_client,
            exe='patch',
            args=args,
            loop=self.loop,
            pipe_in=Just(diff))
        return self.run(job)

__all__ = ('Patch',)
