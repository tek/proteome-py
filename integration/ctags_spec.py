import sure  # NOQA
from flexmock import flexmock  # NOQA

from tek.test import later

from tryp import List

from integration._support.base import VimIntegrationSpec


class _CtagsSpec(VimIntegrationSpec):

    def _pre_start(self):
        self.tag_file = self.main_project / '.tags'

    @property
    def _plugins(self):
        return List(
            'proteome.plugins.ctags',
        )


class CtagsGenSpec(_CtagsSpec):

    def _pre_start(self):
        super()._pre_start()
        self.tag_file.should_not.exist

    def gen(self):
        self.vim.cmd('ProSave')
        self._wait_for(lambda: self.tag_file.exists())


class CtagsAddBufferSpec(_CtagsSpec):

    def add_buffer(self):
        tags = lambda: self.vim.current_buffer.optionl('tags')
        later(lambda: tags().should.contain(str(self.tag_file)))
        self.vim.cmd('ProAdd tpe2/dep')
        later(lambda: tags().should.have.length_of(2))
        self.vim.cmd('edit filename')
        later(lambda: tags().should.have.length_of(2))


__all__ = ('CtagsSpec')
