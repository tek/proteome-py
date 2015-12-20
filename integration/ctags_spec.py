import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List

from integration._support.base import VimIntegrationSpec


class CtagsSpec(VimIntegrationSpec):

    @property
    def _plugins(self):
        return List(
            'proteome.plugins.ctags',
        )

    def gen(self):
        tag_file = self.main_project / '.tags'
        tag_file.should_not.exist
        self._pvar_becomes('root_name', self.name1)
        self.vim.cmd('ProSave')
        self._wait_for(lambda: tag_file.exists())

__all__ = ('CtagsSpec')
