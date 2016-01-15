from pathlib import Path
from datetime import datetime

from fn import _  # type: ignore

from tryp.lazy import lazy
from tryp import Map, __, Just

from trypnv.machine import may_handle, message, handle

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.git import History, HistoryT
from proteome.plugins.core import Save, StageIV

Commit = message('Commit')
HistoryPrev = message('HistoryPrev')
HistoryNext = message('HistoryNext')
HistoryBufferPrev = message('HistoryBufferPrev')
HistoryBufferNext = message('HistoryBufferNext')


class Plugin(ProteomeComponent):

    @lazy
    def base(self):
        return self.vim.pdir('history_base').get_or_else(Path('/dev/null'))

    class Transitions(ProteomeTransitions):

        def _sub(self, state):
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
            return self._sub(new_state)

        def _repos(self, f):
            g = lambda hist, pro: hist // __.at(pro, _ // f)
            new_state = self.projects.fold_left(self.history)(g).state
            return self._sub(new_state)

        def _repo(self, pro, f):
            new_state = (self.history // __.at(pro, _ // f)).state
            return self._sub(new_state)

        def _current_repo(self, f):
            return self.current.map(lambda a: self._repo(a, f))

        @may_handle(StageIV)
        def stage_4(self):
            return self._repos(lambda a: Just(a.state))

        # TODO handle broken repo
        # TODO only save if changes exist
        @may_handle(Commit)
        def commit(self):
            return self._repos(__.add_commit_all(self._timestamp))

        @handle(HistoryPrev)
        def prev(self):
            return self._current_repo(__.prev())

        # FIXME save first?
        @handle(HistoryNext)
        def next(self):
            return self._current_repo(__.next())

        @may_handle(HistoryBufferPrev)
        def history_buffer_prev(self):
            pass

        @may_handle(Save)
        def save(self):
            return Commit()

        @property
        def _timestamp(self):
            return datetime.now().isoformat()

__all__ = ('Commit', 'Plugin', 'HistoryPrev', 'HistoryNext',
           'HistoryBufferPrev', 'HistoryBufferNext')
