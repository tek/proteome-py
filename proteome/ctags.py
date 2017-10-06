from typing import Tuple

from proteome.project import Project
from ribosome.process import NvimProcessExecutor, Job, Result

from amino import Future, Lists, Either, L, _, List


def custom_cmd(cmd: str, project: Project, langs: str, args_tmpl: Either[str, str]) -> Tuple[str, List[str]]:
    args_line = (args_tmpl | '').format(tag_file=project.tag_file, langs=langs, root=project.root)
    args = Lists.split(args_line, ' ')
    return cmd, args


def default_cmd(project: Project, langs: str) -> Tuple[str, List[str]]:
    args = List(
        '-R',
        '--languages={}'.format(langs),
        '-f',
        str(project.tag_file),
        str(project.root)
    )
    return 'ctags', args


class CtagsExecutor(NvimProcessExecutor):

    def gen(self, project: Project, cmd: Either[str, str], args_tmpl: Either[str, str]) -> Future[Result]:
        langs = ','.join(project.ctags_langs)
        exe, args = cmd / L(custom_cmd)(_, project, langs, args_tmpl) | L(default_cmd)(project, langs)
        job = Job(
            client=project.job_client,
            exe=exe,
            args=args,
            loop=self.loop
        )
        return self.run(job)

__all__ = ('CtagsExecutor',)
