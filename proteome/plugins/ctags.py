from fn import _

from trypnv.machine import may_handle, message, handle
from trypnv.nvim import Buffer

from tryp import List, Empty
from tryp.lazy import lazy

from proteome.state import ProteomeComponent
from proteome.env import Env
from proteome.ctags import Ctags
from proteome.plugins.core import Save, Added, BufEnter, StageIV

Gen = message('Gen', 'project')
GenAll = message('GenAll')
Kill = message('Kill')
CurrentBuffer = message('CurrentBuffer')


class Plugin(ProteomeComponent):

    @property
    def ctags(self) -> Ctags:
        return self._ctags  # type: ignore

    @lazy
    def _ctags(self):
        return Ctags(self.vim)

    @property
    def _tags_file_name(self):
        return '.tags'

    @handle(Gen)
    async def gen(self, env, msg):
        await self.ctags.gen(msg.project)
        return Empty()

    @may_handle(StageIV)
    def stage_4(self, env: Env, msg):
        return GenAll(), CurrentBuffer()

    @may_handle(Save)
    def save(self, env: Env, msg):
        return GenAll()

    @may_handle(GenAll)
    def gen_all(self, env: Env, msg):
        if self.ctags.ready:
            return env.projects.projects\
                .filter(_.want_ctags)\
                .map(Gen)

    # TODO kill dangling procs
    @may_handle(Kill)
    def kill(self, env: Env, msg):
        pass

    @may_handle(BufEnter)
    def buf_enter(self, env, msg):
        self.set_buffer_tags(env, List(msg.buffer))

    @may_handle(Added)
    def added(self, env: Env, msg: Added):
        return CurrentBuffer()

    @may_handle(CurrentBuffer)
    def buffer(self, env: Env, msg):
        self.set_buffer_tags(env, List(self.vim.buffer))

    def set_buffer_tags(self, env: Env, bufs: List[Buffer]):
        files = env.all_projects.map(_.root / self._tags_file_name)
        bufs.foreach(lambda a: a.amend_optionl('tags', files))

__all__ = ('GenAll', 'Plugin')
