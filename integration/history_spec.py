import sure  # NOQA
from flexmock import flexmock  # NOQA

from tryp.test import later

from tryp import List, Just, __
from tryp.util.random import Random

from proteome.project import Project

from integration._support.base import VimIntegrationSpec


class _HistorySpec(VimIntegrationSpec):

    def _pre_start(self):
        super()._pre_start()
        self.vim.set_pvar('all_projects_history', True)
        self.test_file_1 = self.main_project / 'test_file_1'
        self.test_content = List(
            'content_1',
            'content_2',
            'content_3',
        )
        self.test_file_1.write_text(self.test_content[0])
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
        self._log_line(-1, __.startswith('#1'))


class HistoryLogSpec(_HistorySpec):

    def logg(self):
        self._save()
        self._write_file(1)
        self._save()
        self._write_file(2)
        self._save()
        self.vim.cmd('ProHistoryLog')
        self._log_line(-3, __.startswith('*'))
        self.vim.cmd('ProHistoryPrev')
        self._await_commit(1)
        self.vim.cmd('ProHistoryLog')
        self._log_line(-2, __.startswith('*'))


class HistoryBrowseSpec(_HistorySpec):

    def browse(self):
        def check(index, start):
            def checker():
                buf = self.vim.buffer.target
                len(buf).should.be.greater_than(max(3, index + 1))
                buf[index].decode().startswith(start).should.be.ok
            later(checker)
        self._debug = True
        marker_text = Random.string()
        self.vim.buffer.set_content([marker_text])
        self._save()
        self._write_file(1)
        self._save()
        self._write_file(2)
        self._save()
        self.vim.cmd('ProHistoryBrowse')
        check(0, '*')
        check(1, 'diff')
        self.vim.vim.feedkeys('j')
        check(1, ' ')
        check(2, 'diff')
        self.vim.vim.feedkeys('k')
        self.vim.vim.feedkeys('k')
        check(1, 'diff')
        self.vim.vim.feedkeys('j')
        self.vim.vim.feedkeys('j')
        self.vim.vim.feedkeys('s')
        self._await_commit(0)
        self.vim.buffer.content.should.equal(List(marker_text))
        self.vim.cmd('ProHistoryBrowse')
        check(-1, '*')
        self.vim.vim.feedkeys('j')
        self.vim.vim.feedkeys('s')
        self._await_commit(1)
        self.vim.buffer.content.should.equal(List(marker_text))

__all__ = ('HistorySwitchSpec', 'HistoryLogSpec')
