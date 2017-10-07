from typing import Generator, Tuple

from amino import List, _, do, __, Either, Future, Lists, L, I
from amino.do import tdo

from ribosome.machine.message_base import Message
from ribosome.nvim import Buffer, NvimIO
from ribosome.machine.messages import Stage4, Nop, Error, SubProcessAsync
from ribosome.machine.state import SubTransitions
from ribosome.machine import trans
from ribosome.nvim.io import NvimIOState
from ribosome.process import Result, Job

from proteome.components.core import Save, Added, BufEnter
from proteome.env import Env
from proteome.project import Project
from proteome.components.ctags.messages import CurrentBuffer, Gen, Kill, GenAll


def custom_cmd(cmd: str, args: Either[str, str]) -> Tuple[str, str]:
    return cmd, args | ''


default_cmd = 'ctags', '-R --languages={langs} -f {tag_file} {root}'


def subproc_job(project: Project, cmd: Either[str, str], args_tmpl: Either[str, str]) -> Future[Result]:
    langs = ','.join(project.ctags_langs)
    exe, args_line = cmd / L(custom_cmd)(_, args_tmpl) | default_cmd
    args = args_line.format(tag_file=project.tag_file, langs=langs, root=project.root)
    args_tok = Lists.split(args, ' ')
    return Job(
        client=project.job_client,
        exe=exe,
        args=args_tok,
        loop=None,
    )


@tdo(NvimIOState[Env, Job])
def gen(project: Project) -> Generator:
    settings = yield NvimIOState.inspect(_.settings)
    cmd = yield NvimIOState.lift(settings.tags_command.value)
    args = yield NvimIOState.lift(settings.tags_args.value)
    yield NvimIOState.pure(subproc_job(project, cmd, args))


class Ctags(SubTransitions):

    @property
    def _tags_file_name(self) -> str:
        return '.tags'

    @trans.multi(Stage4)
    def stage_4(self) -> List[Message]:
        return List(GenAll(), CurrentBuffer())

    @trans.one(Save)
    def save(self) -> Message:
        return GenAll()

    @trans.multi(GenAll)
    def gen_all(self) -> List[Message]:
        return self.data.projects.projects.filter(_.want_ctags).map(Gen)

    # TODO kill dangling procs
    @trans.unit(Kill)
    def kill(self) -> None:
        pass

    @trans.unit(BufEnter)
    def buf_enter(self) -> None:
        return self.set_buffer_tags(List(self.msg.buffer))

    @trans.one(Added)
    def added(self: Added) -> Message:
        return CurrentBuffer()

    @trans.unit(CurrentBuffer, trans.nio)
    @tdo(NvimIO[None])
    def buffer(self) -> Generator:
        buf = yield NvimIO(_.buffer)
        yield NvimIO.pure(self.set_buffer_tags(List(buf)))

    def set_buffer_tags(self, bufs: List[Buffer]) -> None:
        files = self.data.all_projects.map(_.root / self._tags_file_name)
        bufs.foreach(__.options.amend_l('tags', files))

    @trans.one(Gen, trans.st)
    @do
    def gen(self) -> Generator:
        job = yield gen(self.msg.project)
        def result(result: Result) -> Message:
            return (
                Nop().pub
                if result.success else
                Error(f'failed to generate tags for {self.msg.project}: {result.msg}').pub
            )
        yield NvimIOState.pure(SubProcessAsync(job, result).pub)


__all__ = ('GenAll', 'Ctags')
