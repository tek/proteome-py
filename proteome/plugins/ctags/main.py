from fn import _

from ribosome.machine import may_handle, message
from ribosome.nvim import Buffer

from amino import List, Empty
from amino.lazy import lazy

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.ctags import Ctags
from proteome.plugins.core import Save, Added, BufEnter, StageIV

Gen = message('Gen', 'project')
GenAll = message('GenAll')
Kill = message('Kill')
CurrentBuffer = message('CurrentBuffer')


class CtagsTransitions(ProteomeTransitions):

    @property
    def ctags(self) -> Ctags:
        return self.machine.ctags  # type: ignore

    @property
    def _tags_file_name(self):
        return '.tags'

    @may_handle(StageIV)
    def stage_4(self):
        return GenAll(), CurrentBuffer()

    @may_handle(Save)
    def save(self):
        return GenAll()

    @may_handle(GenAll)
    def gen_all(self):
        if self.ctags.ready:
            return self.data.projects.projects\
                .filter(_.want_ctags)\
                .map(Gen)

    # TODO kill dangling procs
    @may_handle(Kill)
    def kill(self):
        pass

    @may_handle(BufEnter)
    def buf_enter(self):
        self.set_buffer_tags(List(self.msg.buffer))

    @may_handle(Added)
    def added(self: Added):
        return CurrentBuffer()

    @may_handle(CurrentBuffer)
    def buffer(self):
        self.set_buffer_tags(List(self.vim.buffer))

    def set_buffer_tags(self, bufs: List[Buffer]):
        files = self.data.all_projects.map(_.root / self._tags_file_name)
        bufs.foreach(lambda a: a.options.amend_l('tags', files))

    @may_handle(Gen)
    async def gen(self):
        await self.ctags.gen(self.msg.project)
        return Empty()


class Plugin(ProteomeComponent):
    Transitions = CtagsTransitions

    @lazy
    def ctags(self):
        return Ctags(self.vim)

__all__ = ('GenAll', 'Plugin')
