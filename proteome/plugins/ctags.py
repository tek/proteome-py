from fn import _  # type: ignore

from trypnv.machine import may_handle, message
from trypnv.nvim import Buffer

from tryp import List

from proteome.state import ProteomeComponent
from proteome.env import Env
from proteome.ctags import Ctags
from proteome.project import Project
from proteome.plugins.core import Save, Added, BufEnter

Gen = message('Gen')
Kill = message('Kill')


class Plugin(ProteomeComponent):

    ctags = Ctags()

    @property
    def _tags_file_name(self):
        return '.tags'

    def _gen(self, pro: Project):
        return self.ctags.gen(pro)

    @may_handle(Save)
    def save(self, env: Env, msg):
        return self.gen(env, msg)

    @may_handle(Gen)
    def gen(self, env: Env, msg):
        if self.ctags.ready:
            env.projects.projects\
                .filter(_.want_ctags)\
                .map(self._gen)
            self.ctags.exec_pending()

    # TODO kill dangling procs
    @may_handle(Kill)
    def kill(self, env: Env, msg):
        pass

    @may_handle(BufEnter)
    def buf_enter(self, env, msg):
        self.set_buffer_tags(env, List(msg.buffer))

    # FIXME need to use setlocal for all buffers, this is ineffective
    @may_handle(Added)
    def added(self, env: Env, msg: Added):
        if env.initialized:
            bufs = self.vim.buffers
        else:
            bufs = List(self.vim.current_buffer)
        self.set_buffer_tags(env, bufs)

    def set_buffer_tags(self, env: Env, bufs: List[Buffer]):
        files = env.all_projects.map(_.root / self._tags_file_name)
        bufs.foreach(lambda a: a.amend_optionl('tags', files))

__all__ = ['Gen', 'Plugin']
