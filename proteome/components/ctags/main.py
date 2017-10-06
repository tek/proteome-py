from typing import Generator, Any

from amino import List, _, Nil, do, __
from amino.do import tdo

from ribosome.machine.message_base import message, Message
from ribosome.machine.transition import may_handle
from ribosome.nvim import Buffer, NvimIO
from ribosome.machine.messages import Stage4, Nop, Error
from ribosome.machine.state import SubTransitions
from ribosome.machine import trans
from ribosome.nvim.io import NvimIOState

from proteome.ctags import CtagsExecutor
from proteome.components.core import Save, Added, BufEnter
from proteome.env import Env
from proteome.project import Project

Gen = message('Gen', 'project')
GenAll = message('GenAll')
Kill = message('Kill')
CurrentBuffer = message('CurrentBuffer')


@tdo(NvimIOState[Env, None])
def gen(project: Project) -> Generator:
    settings = yield NvimIOState.inspect(_.settings)
    cmd = yield NvimIOState.lift(settings.tags_command.value)
    args = yield NvimIOState.lift(settings.tags_args.value)
    executor = yield NvimIOState.io(lambda v: CtagsExecutor(v))
    yield NvimIOState.pure(executor.gen(project, cmd, args))


class Ctags(SubTransitions):

    @property
    def executor(self) -> NvimIO[CtagsExecutor]:
        return NvimIO(lambda v: CtagsExecutor(v))

    @property
    def _tags_file_name(self) -> str:
        return '.tags'

    @may_handle(Stage4)
    def stage_4(self):
        return GenAll(), CurrentBuffer()

    @may_handle(Save)
    def save(self):
        return GenAll()

    @trans.multi(GenAll, trans.nio)
    @do
    def gen_all(self):
        exe = yield self.executor
        yield NvimIO.pure(self.data.projects.projects.filter(_.want_ctags).map(Gen) if exe.ready else Nil)

    # TODO kill dangling procs
    @may_handle(Kill)
    def kill(self):
        pass

    @trans.unit(BufEnter)
    def buf_enter(self) -> None:
        return self.set_buffer_tags(List(self.msg.buffer))

    @may_handle(Added)
    def added(self: Added):
        return CurrentBuffer()

    @trans.unit(CurrentBuffer, trans.nio)
    @do
    def buffer(self) -> Generator[NvimIO[None], Any, None]:
        buf = yield NvimIO(_.buffer)
        yield NvimIO.pure(self.set_buffer_tags(List(buf)))

    def set_buffer_tags(self, bufs: List[Buffer]):
        files = self.data.all_projects.map(_.root / self._tags_file_name)
        bufs.foreach(__.options.amend_l('tags', files))

    @trans.one(Gen, trans.st, trans.coro)
    @do
    def gen(self) -> Generator:
        coro = yield gen(self.msg.project)
        async def result() -> Message:
            result = await coro
            return (
                Nop().pub
                if result.success else
                Error(f'failed to generate tags for {self.msg.project}: {result.msg}').pub
            )
        yield NvimIOState.pure(result())


__all__ = ('GenAll', 'Ctags')
