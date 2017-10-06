from typing import Tuple

from proteome.project import Project
from ribosome.process import NvimProcessExecutor, Job, Result

from amino import Future, Lists, Either, L, _


def custom_cmd(cmd: str, args: Either[str, str]) -> Tuple[str, str]:
    return cmd, args | ''


default_cmd = 'ctags', '-R --languages={langs} -f {tag_file} {root}'


class CtagsExecutor(NvimProcessExecutor):

    def gen(self, project: Project, cmd: Either[str, str], args_tmpl: Either[str, str]) -> Future[Result]:
        langs = ','.join(project.ctags_langs)
        exe, args_line = cmd / L(custom_cmd)(_, args_tmpl) | default_cmd
        args = args_line.format(tag_file=project.tag_file, langs=langs, root=project.root)
        args_tok = Lists.split(args, ' ')
        job = Job(
            client=project.job_client,
            exe=exe,
            args=args_tok,
            loop=self.loop
        )
        return self.run(job)

__all__ = ('CtagsExecutor',)
