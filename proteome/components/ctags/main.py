from typing import Generator, Any

from amino import List, _, Nil, do, __

from ribosome.machine.message_base import message
from ribosome.machine.transition import may_handle
from ribosome.nvim import Buffer, NvimIO
from ribosome.machine.messages import Stage4
from ribosome.machine.state import SubTransitions
from ribosome.machine import trans

from proteome.ctags import CtagsExecutor
from proteome.components.core import Save, Added, BufEnter

Gen = message('Gen', 'project')
GenAll = message('GenAll')
Kill = message('Kill')
CurrentBuffer = message('CurrentBuffer')


class Ctags(SubTransitions):

    @property
    def executor(self) -> NvimIO[CtagsExecutor]:
        return NvimIO(CtagsExecutor)

    @property
    def _tags_file_name(self):
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

    @trans.unit(Gen, trans.nio, trans.coro)
    @do
    def gen(self):
        exe = yield self.executor
        yield NvimIO.pure(exe.gen(self.msg.project))


__all__ = ('GenAll', 'Ctags')