from pathlib import Path
from datetime import datetime

from fn import _  # type: ignore

from pyrsistent import PRecord

from tryp.lazy import lazy
from tryp import Map, __, Just, Empty

from trypnv.machine import may_handle, message, handle
from trypnv.data import field, list_field
from trypnv.nvim import Buffer

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.git import History, HistoryT
from proteome.plugins.core import Save, StageIV

Commit = message('Commit')
HistoryPrev = message('HistoryPrev')
HistoryNext = message('HistoryNext')
HistoryBufferPrev = message('HistoryBufferPrev')
HistoryBufferNext = message('HistoryBufferNext')
HistoryStatus = message('HistoryStatus')
HistoryLog = message('HistoryLog')
HistoryBrowse = message('HistoryBrowse')


class Plugin(ProteomeComponent):

    @lazy
    def base(self):
        return self.vim.pdir('history_base').get_or_else(Path('/dev/null'))

    class Transitions(ProteomeTransitions):

        def _with_sub(self, state):
            return self.data.with_sub_state(self.name, state)

        @lazy
        def history(self):
            return HistoryT(History(
                self.machine.base, state=self.data.sub_state(self.name, Map)))

        @property
        def all_projects_history(self):
            return self.pflags.all_projects_history

        @lazy
        def projects(self):
            return self.data.history_projects(self.all_projects_history)

        @property
        def current(self):
            return self.data.current

        def _all_projects(self, f):
            new_state = self.projects.fold_left(self.history)(f).state
            return self._with_sub(new_state)

        def _with_repos(self, f):
            g = lambda hist, pro: hist / __.at(pro, _ / f)
            new_state = self.projects.fold_left(self.history)(g).state
            return self._with_sub(new_state)

        def _with_repo(self, pro, f):
            new_state = (self.history / __.at(pro, f)).state
            return self._with_sub(new_state)

        def _with_current_repo(self, f):
            return self.current.map(lambda a: self._with_repo(a, f))

        @may_handle(StageIV)
        def stage_4(self):
            return self._with_repos(lambda a: Just(a.state))

        # TODO handle broken repo
        # TODO only save if changes exist
        # TODO allow specifying target
        @may_handle(Commit)
        def commit(self):
            return self._with_repos(__.add_commit_all(self._timestamp))

        def _switch(self, f):
            def notify(repo):
                self.vim.reload_windows()
                repo.current_commit_info\
                    .map(lambda a: '#{} {}'.format(a.num, a.since))\
                    .foreach(self.log.info)
                return repo
            return self._with_current_repo(_ / f % notify)

        # FIXME save first?
        @handle(HistoryPrev)
        def prev(self):
            return self._switch(__.prev())

        @handle(HistoryNext)
        def next(self):
            return self._switch(__.next())

        @may_handle(HistoryBufferPrev)
        def history_buffer_prev(self):
            pass

        @may_handle(HistoryStatus)
        def history_status(self):
            def log_status(repo):
                if repo.status:
                    msg = 'history repo dirty'
                else:
                    msg = 'history repo clean'
                self.log.info(msg)
                return Empty()
            self._with_current_repo(log_status)

        @may_handle(HistoryLog)
        def history_log(self):
            self._with_current_repo(
                _ % (lambda r: self.vim.multi_line_info(r.log_formatted))
            )
        @may_handle(Save)
        def save(self):
            return Commit()

        @property
        def _timestamp(self):
            return datetime.now().isoformat()

__all__ = ('Commit', 'Plugin', 'HistoryPrev', 'HistoryNext',
           'HistoryBufferPrev', 'HistoryBufferNext')
