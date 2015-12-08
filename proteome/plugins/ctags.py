from fn import _  # type: ignore

from trypnv.machine import may_handle, message

from proteome.state import ProteomeComponent
from proteome.env import Env
from proteome.ctags import Ctags
from proteome.project import Project

Gen = message('Gen')
Kill = message('Kill')


class Plugin(ProteomeComponent):

    ctags = Ctags()

    def _gen(self, pro: Project):
        return self.ctags.gen(pro)

    @may_handle(Gen)
    def gen(self, env: Env, msg):
        if self.ctags.ready:
            env.projects.projects\
                .filter(_.want_ctags)\
                .map(self._gen)

    # TODO kill dangling procs
    @may_handle(Kill)
    def kill(self, env: Env, msg):
        pass

__all__ = ['Gen', 'Plugin']
