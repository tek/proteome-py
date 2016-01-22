from proteome.project import Project
from trypnv import ProcessExecutor, Job  # type: ignore


class Patch(ProcessExecutor):  # type: ignore

    def gen(self, project: Project):
        args = [
            str(project.root)
        ]
        job = Job(project, 'patch', args, self.loop)
        return self.run(job)

__all__ = ('Patch',)
