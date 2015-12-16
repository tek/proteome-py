from proteome.project import Project
from trypnv import ProcessExecutor, Job  # type: ignore


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
        job = Job(project, 'ctags', args, self.loop)
        return self.run(job)

__all__ = ['Ctags']
