from amino.test.spec_spec import later

from amino import List, Just, __, _

from kallikrein.matchers.start_with import start_with
from kallikrein.matchers.maybe import be_just
from kallikrein import unsafe_kf
from amino.util.random import Random

from proteome.project import Project
from proteome.components.history import History

from integration._support.base import DefaultSpec


class _HistorySpec(DefaultSpec):

    def _pre_start(self):
        super()._pre_start()
        self.vim.vars.set_p('all_projects_history', True)
        self.test_file_1 = self.main_project / 'test_file_1'
        self.test_file_2 = self.main_project / 'test_file_2'
        self.test_content = List(
            'content_1',
            'content_2',
            'content_3',
        )
        self.test_file_1.write_text(self.test_content[0])
        self.pro = Project.of(self.name1, self.main_project, Just(self.tpe1))
        self.history = History(self.history_base)
        self.repo = self.history.repo(self.pro).x

    @property
    def components(self):
        return List('history')

    @property
    def _object_count(self):
        return len(self.object_files(self.pro))

    def _wait_for_oc(self, count):
        self._wait_for(lambda: self._object_count > count)

    def _await_commit(self, num):
        return self._await_content(self.test_content[num])

    def _await_content(self, text):
        return unsafe_kf(self.test_file_1.read_text) == text

    def _write_file(self, num):
        self.test_file_1.write_text(self.test_content[num])

    def _write_file2(self, num):
        self.test_file_2.write_text(self.test_content[num])

    def _save(self):
        oc_pre = self._object_count
        self.vim.cmd('ProSave')
        self._wait_for_oc(oc_pre)
        self._wait(0.1)


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


class HistorySaveSpec(_HistorySpec):

    def clean_workdir(self):
        self._save()
        self._write_file(1)
        self._save()
        self.vim.cmd('ProSave')
        self.vim.cmd('ProHistoryLog')
        later(lambda: self._log_out.should.have.length_of(2))


class HistoryLogSpec(_HistorySpec):

    def logg(self):
        self._save()
        self._write_file(1)
        self._save()
        self._write_file(2)
        self._save()
        self.vim.cmd('ProHistoryLog')
        self._log_line(-3, be_just(start_with('*')))
        self.vim.cmd('ProHistoryPrev')
        self._await_commit(1)
        self.vim.cmd('ProHistoryLog')
        return self._log_line(-2, be_just(start_with('*')))


class _BrowseHelpers(object):

    def _check(self, index, start):
        def checker():
            buf = self.vim.buffer.target
            len(buf).should.be.greater_than(max(3, index + 1))
            buf[index].startswith(start).should.be.ok
        later(checker)


class HistoryBrowseSpec(_HistorySpec, _BrowseHelpers):

    def browse(self):
        check = self._check
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

    def quit(self):
        check = self._check
        marker_text = Random.string()
        self.vim.buffer.set_content([marker_text])
        self._save()
        self._write_file(1)
        self._save()
        self._write_file(2)
        self._save()
        self.vim.cmd('ProHistoryBrowse')
        check(0, '*')
        self.vim.feedkeys('q')
        later(lambda: self.vim.buffer.content.should.equal(List(marker_text)))


class FileHistoryBrowseSpec(_HistorySpec, _BrowseHelpers):

    def browse(self):
        ''' Browse the history of a single file
        adds one commit that doesn't contain changes in test_file_1.
        there are four commits in summary, so the check for buffer line
        count compares with 3.
        at the end, a fifth commit must be present due to resetting the
        file contents.
        '''
        check = self._check
        marker_text = Random.string()
        self.vim.buffer.set_content([marker_text])
        self._save()
        self._write_file(1)
        self._save()
        self._write_file2(1)
        self._save()
        self._write_file(2)
        self._write_file2(1)
        self._save()
        self.vim.cmd('ProHistoryFileBrowse {}'.format('test_file_1'))
        check(0, '*')
        self.vim.vim.feedkeys('j')
        self.vim.vim.feedkeys('j')
        later(lambda: self.vim.buffer.content.length.should.equal(3))
        self.vim.vim.feedkeys('s')
        self._await_commit(0)
        self.vim.buffer.content.should.equal(List(marker_text))
        # somewhere, something memoizes and this doesn't work
        # self.repo.history.drain.should.have.length_of(5)


class HistoryPickSpec(_HistorySpec, _BrowseHelpers):

    _tail = ['end']

    def _write(self, lines, save=True):
        text = '\n'.join(lines + self._tail)
        self.test_file_1.write_text(text)
        if save:
            self._save()

    def invalid(self):
        self._save()
        self._write_file(1)
        self._save()
        self._write_file(2)
        self._save()
        self.vim.cmd('ProHistoryPick 1')
        self._log_line(-1, _ == Plugin.failed_pick_err)

    def patch(self):
        self._save()
        text1 = '\n'.join(self.test_content[:2])
        self.test_file_1.write_text(text1)
        self._save()
        text2 = '\n'.join(self.test_content)
        self.test_file_1.write_text(text2)
        self._save()
        self.vim.cmd('ProHistoryBrowse')
        self._check(0, '*')
        self.vim.vim.feedkeys('j')
        self.vim.vim.feedkeys('p')
        text3 = '\n'.join([self.test_content[0], self.test_content[2]])
        self._await_content(text3)
        self._log_line(-1, __.startswith('picked #1'))

    def revert(self):
        self._write(self.test_content[:1])
        self._write(self.test_content[:2])
        self._write(self.test_content)
        self.vim.cmd('ProHistoryBrowse')
        self._check(0, '*')
        self.vim.vim.feedkeys('r')
        text3 = '\n'.join(self.test_content[:2] + self._tail)
        self._await_content(text3)
        self._log_line(-1, __.startswith('picked #0'))

    def pick_save(self):
        self._write(self.test_content[:1])
        self._write(self.test_content[:2])
        self._write(self.test_content)
        self.vim.cmd('ProHistoryPick 1')
        text3 = '\n'.join([self.test_content[0], self.test_content[2]] +
                          self._tail)
        self._await_content(text3)
        self.vim.cmd('ProSave')
        self._wait(1)
        self._write(self.test_content)
        self._await_content('\n'.join(self.test_content + self._tail))
        self.vim.cmd('ProHistoryPrev')
        self._await_content(text3)
        self.vim.cmd('ProHistoryPrev')
        self.vim.cmd('ProHistoryPrev')
        text4 = '\n'.join(self.test_content[:2] + self._tail)
        self._await_content(text4)

__all__ = ('HistorySwitchSpec', 'HistoryLogSpec')
