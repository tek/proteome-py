import sure  # NOQA
from flexmock import flexmock  # NOQA

from tek.test import later

from tryp import List, Just

from proteome.project import Project

from integration._support.base import VimIntegrationSpec


class _HistorySpec(VimIntegrationSpec):

    def _pre_start(self):
        super()._pre_start()
        self.vim.set_pvar('all_projects_history', True)
        self.test_file_1 = self.main_project / 'test_file_1'
        self.test_content_1 = 'content_1'
        self.test_content_2 = 'content_2'
        self.test_content_3 = 'content_3'
        self.test_content = List(
            self.test_content_1,
            self.test_content_2,
            self.test_content_3,
        )
        self.test_file_1.write_text(self.test_content_1)
        self.pro = Project.of(self.name1, self.main_project, Just(self.tpe1))

    @property
    def _plugins(self):
        return List(
            'proteome.plugins.history',
        )

    @property
    def _object_count(self):
        return len(self.object_files(self.pro))

    def _wait_for_oc(self, count):
        self._wait_for(lambda: self._object_count > count)

    def _await_commit(self, num):
        def checker():
            self.test_file_1.read_text()\
                .should.equal(self.test_content[num])
        later(checker)

    def _write_file(self, num):
        self.test_file_1.write_text(self.test_content[num])

    def _save(self):
        oc_pre = self._object_count
        self.vim.cmd('ProSave')
        self._wait_for_oc(oc_pre)


class HistorySwitchSpec(_HistorySpec):

    def prev_next(self):
        self._save()
        self._write_file(1)
        self._save()
        self.vim.cmd('ProHistoryPrev')
        self._await_commit(0)
        self.vim.cmd('ProHistoryNext')
        self._await_commit(1)

    def prev_save(self):
        self._save()
        self._write_file(1)
        self._save()
        self.vim.cmd('ProHistoryPrev')
        self._await_commit(0)
        self._write_file(2)
        self._save()
        self.vim.cmd('ProHistoryPrev')
        self._await_commit(1)
        self._log_out[-1][:2].should.equal('#1')


class HistoryLogSpec(_HistorySpec):

    def logg(self):
        self._save()
        self._write_file(1)
        self._save()
        self._write_file(2)
        self._save()
        self.vim.cmd('ProHistoryLog')
        later(lambda: self._log_out[-3][0].should.equal('*'))
        self.vim.cmd('ProHistoryPrev')
        self._await_commit(1)
        self.vim.cmd('ProHistoryLog')
        later(lambda: self._log_out[-2][0].should.equal('*'))

__all__ = ('HistorySwitchSpec', 'HistoryLogSpec')
