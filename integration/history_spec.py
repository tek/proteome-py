import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp import List, Just

from proteome.project import Project

from integration._support.base import VimIntegrationSpec


class _HistorySpec(VimIntegrationSpec):

    def _pre_start(self):
        super()._pre_start()
        self.vim.set_pvar('all_projects_history', True)

    @property
    def _plugins(self):
        return List(
            'proteome.plugins.history',
        )


class HistorySwitchSpec(_HistorySpec):

    def _pre_start(self):
        super()._pre_start()
        self.test_file_1 = self.main_project / 'test_file_1'
        self.test_content_1 = 'content_1'
        self.test_content_2 = 'content_2'
        self.test_file_1.write_text(self.test_content_1)
        self.pro = Project.of(self.name1, self.main_project, Just(self.tpe1))

    @property
    def _object_count(self):
        return len(self.object_files(self.pro))

    def _wait_for_oc(self, count):
        self._wait_for(lambda: self._object_count > count)

    def prev(self):
        self._debug = True
        self.vim.cmd('ProSave')
        self._wait_for_oc(2)
        self.test_file_1.write_text(self.test_content_2)
        self.vim.cmd('ProSave')
        self.vim.cmd('ProHistoryPrev')
        self._wait_for(
            lambda: self.test_file_1.read_text() == self.test_content_1)
        self.vim.cmd('ProHistoryNext')
        self._wait_for(
            lambda: self.test_file_1.read_text() == self.test_content_2)

__all__ = ('HistorySwitchSpec')
