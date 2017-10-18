from amino import List

from kallikrein import kf, unsafe_k, Expectation
from kallikrein.matchers import contain
from kallikrein.matchers.length import have_length

from ribosome.test.integration.klk import later

from integration._support.base import DefaultSpec


class _CtagsSpec(DefaultSpec):

    def _pre_start(self) -> None:
        self.tag_file = self.main_project / '.tags'

    @property
    def components(self) -> List[str]:
        return List('ctags')


class CtagsGenSpec(_CtagsSpec):
    '''generate ctags files
    default generation $gen
    custom generation $gen_custom
    '''

    def _pre_start(self):
        super()._pre_start()
        unsafe_k(self.tag_file.exists()).false

    def gen(self) -> Expectation:
        self.cmd_sync('ProSave')
        later(kf(self.tag_file.exists).true)
        self.tag_file.unlink()
        self.cmd_sync('ProSave')
        return later(kf(self.tag_file.exists).true)

    def gen_custom(self) -> Expectation:
        tag_file = self.main_project / '.tags_custom'
        self.vim.vars.set_p('tags_command', 'ctags')
        self.vim.vars.set_p('tags_args', f'-R -f {tag_file} {{root}}')
        self.cmd_sync('ProSave')
        later(kf(tag_file.exists).true)
        self.tag_file.unlink()
        self.cmd_sync('ProSave')
        return later(kf(tag_file.exists).true)


class CtagsAddBufferSpec(_CtagsSpec):
    '''set the 'tags' option when adding a buffer $add_buffer
    '''

    def add_buffer(self):
        tags = lambda: self.vim.buffer.options.l('tags')
        later(kf(tags).must(contain(str(self.tag_file))))
        self.cmd_sync('ProAdd! tpe2/dep')
        later(kf(tags).must(have_length(2)))
        self.cmd_sync('new')
        return later(kf(tags).must(have_length(2)))


__all__ = ('CtagsAddBufferSpec', 'CtagsGenSpec')
