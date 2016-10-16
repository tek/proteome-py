from pathlib import Path
from datetime import datetime

from fn import _, F

from amino.lazy import lazy
from amino import Map, __, Just, Empty, may, List, Maybe, Right
from amino.util.numeric import try_convert_int
from amino.async import gather_sync_flat
from amino.task import Task

from ribosome.machine import may_handle, message, handle, Info
from ribosome.machine import Error
from ribosome.record import field, dfield, Record, lazy_list_field, maybe_field
from ribosome.nvim import ScratchBuilder, ScratchBuffer
from ribosome.machine.base import UnitTask

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.plugins.core import Save, StageIV
from proteome.logging import Logging
from proteome.project import Project
from proteome.git import Repo, CommitInfo
from proteome.plugins.history.messages import (HistoryPrev, HistoryNext,
                                               HistoryStatus, HistoryLog,
                                               HistoryBrowse,
                                               HistoryBrowseInput,
                                               HistorySwitch, Redraw,
                                               QuitBrowse, Commit,
                                               HistoryBufferPrev, HistoryPick,
                                               HistoryRevert,
                                               HistoryFileBrowse,
                                               HistorySwitchFile,
                                               CommitCurrent)
from proteome.plugins.history.data import History, HistoryT, HistoryState
from proteome.plugins.history.process import HistoryGit
from proteome.plugins.history.patch import Patch


class BrowseState(Record):
    repo = field(Repo)
    current = field(int)
    commits = lazy_list_field()
    buffer = field(ScratchBuffer)
    selected = dfield(0)
    path = maybe_field(Path)

Init = message('Init')


class BrowseTransitions(ProteomeTransitions):

    @property
    def buffer(self):
        return self.data.buffer.proxy

    @lazy
    def content(self):
        sel = self.data.selected
        return List.wrap(enumerate(self.data.commits[:sel + 20]))\
            .flat_smap(lambda i, a: a.browse_format(i == sel))

    @property
    def selected_commit(self):
        return self.data.commits.lift(self.data.selected)

    @property
    def selected_id(self):
        return self.selected_commit / _.hex

    def _create_mappings(self):
        List.wrap('jksprq').foreach(self._create_mapping)
        self._create_mapping('<cr>', to='%CR%')

    def _create_mapping(self, keyseq, mode='n', to=None):
        to_seq = Maybe(to) | keyseq
        raw = self.buffer.buffer
        cmd = ':ProHistoryBrowseInput {}<cr>'.format(to_seq)
        raw.nmap(keyseq, cmd)

    def _configure_appearance(self):
        self.buffer.options.set_s('filetype', 'diff')
        self.buffer.options.set_s('syntax', 'diff')
        self.buffer.window.options.set_b('cursorline', True)
        self.vim.doautocmd('FileType')
        sy = self.buffer.syntax
        id_fmt = '[a-f0-9]\+'
        sy.match('Commit', '^[* ]\s\+{}'.format(id_fmt),
                 contains='Star,Sha')
        sy.match('Star', '^*', 'contained')
        sy.match('Sha', id_fmt, 'contained')
        sy.link('Star', 'Title')
        sy.link('Sha', 'Identifier')

    @may_handle(Init)
    def browse_init(self):
        self._create_mappings()
        self._configure_appearance()
        return Redraw()

    @may_handle(Redraw)
    def redraw(self):
        self.buffer.set_content(self.content)
        self.vim.cursor(self.data.selected + 1, 1)
        self.vim.feedkeys('zz')

    @handle(HistoryBrowseInput)
    def input(self):
        handlers = Map({
            'j': self._down,
            'k': self._up,
            '%CR%': self._switch,
            's': self._switch,
            'p': self._pick,
            'r': self._revert,
            'q': self._close_tab,
        })
        return handlers.get(self.msg.keyseq).flat_map(lambda f: f())

    def _down(self):
        return self._select_diff(1)

    def _up(self):
        return self._select_diff(-1)

    @may
    def _select_diff(self, diff):
        index = self.data.selected + diff
        if index >= 0 and self.data.commits.min_length(index + 1):
            return self.data.set(selected=index), Redraw()

    @may
    def _switch(self):
        q = QuitBrowse(self.buffer)
        switch = (
            self.data.path //
            (lambda path: self.selected_id / F(HistorySwitchFile, path)) |
            HistorySwitch(self.data.selected)
        )
        return (switch.pub, q, q.pub)

    @may_handle(QuitBrowse)
    def quit(self):
        if self.msg.buffer == self.buffer:
            self._close_tab()

    @may
    def _close_tab(self):
        self.buffer.close()

    def _pick(self):
        return self._pick_commit(HistoryPick)

    def _revert(self):
        return self._pick_commit(HistoryRevert)

    @may
    def _pick_commit(self, tpe):
        q = QuitBrowse(self.buffer)
        return (tpe(self.data.selected).pub, q, q.pub)


class BrowseMachine(ProteomeComponent):
    Transitions = BrowseTransitions
    _data_type = BrowseState


class Browse(Logging):

    def __init__(self, state: BrowseState, vim) -> None:
        self.state = state
        self.machine = BrowseMachine(vim, title='history_browse')

    @property
    def buffer(self):
        return self.state.buffer

    @property
    def repo(self):
        return self.state.repo

    def run(self):
        return self.send(Init())

    def send(self, msg):
        result = self.machine.loop_process(self.state, msg)
        self.state = result.data
        return result.pub


class Plugin(ProteomeComponent):
    failed_pick_err = 'couldn\'t revert commit'

    @lazy
    def base(self):
        return self.vim.vars.pdir('history_base') | Path('/dev/null')

    @lazy
    def executor(self):
        return HistoryGit(self.base, self.vim)

    class Transitions(ProteomeTransitions):

        @property
        def executor(self):
            return self.machine.executor

        def _with_sub(self, state):
            return self.data.with_sub_state(self.name, state)

        @property
        def _with_browse(self):
            return F(self._with_sub) << self.state.setter('browse')

        @property
        def state(self):
            return self.data.sub_state(self.name, HistoryState)

        @lazy
        def history(self):
            return History(self.machine.base, state=self.state)

        @lazy
        def history_t(self):
            return HistoryT(self.history)

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
            new_state = self.projects.fold_left(self.history_t)(f).state
            return self._with_sub(new_state)

        def _with_repos(self, f):
            g = lambda hist, pro: hist / __.at(pro, _ / f)
            return self._all_projects(g)

        def _with_repo(self, pro, f):
            new_state = (self.history_t / __.at(pro, f)).state
            return self._with_sub(new_state)

        def _with_current_repo(self, f):
            return self.current.map(lambda a: self._with_repo(a, f))

        def _repo_ro(self, project: Project):
            return self.history.repo(project)

        @property
        def _current_repo_ro(self):
            return self.current // self._repo_ro

        @property
        def _repos_ro(self):
            return self.projects // self._repo_ro

        @may_handle(StageIV)
        def stage_4(self):
            ''' initialize repository states '''
            return self._with_repos(lambda a: Just(a.state))

        def _switch(self, f):
            def notify(repo):
                self.vim.reload_windows()
                repo.current_commit_info\
                    .map(_.num_since)\
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

        @handle(HistorySwitch)
        def switch(self):
            return try_convert_int(self.msg.index)\
                .map(__.select)\
                .flat_map(self._switch)

        @handle(HistorySwitchFile)
        def switch_file(self):
            return (
                self._current_repo_ro /
                __.checkout_file(self.msg.id, self.msg.path) /
                __.map(lambda a: CommitCurrent()) /
                UnitTask
            )

        # TODO
        @may_handle(HistoryBufferPrev)
        def history_buffer_prev(self):
            pass

        @may_handle(HistoryStatus)
        def history_status(self):
            def log_status(repo):
                state = 'dirty' if repo.status else 'clean'
                return Info('history repo {}'.format(state)).pub
            self._with_current_repo(_ / log_status)

        @may_handle(HistoryLog)
        def history_log(self):
            self._current_repo_ro / _.log_formatted % self.vim.multi_line_info

        def _build_browse(self, repo, commits, path: Maybe[Path]):
            relpath = path // repo.relpath
            return ScratchBuilder().tab.build.unsafe_perform_io(self.vim)\
                .leffect(self._io_error)\
                .map(lambda a: BrowseState(repo=repo, current=0,
                                           commits=commits, buffer=a,
                                           path=relpath))

        def _browse(self, f, path: Maybe[Path]=Empty()):
            commits = lambda r: (r, f(r))
            return (
                (self._current_repo_ro / commits)
                .flat_smap(F(self._build_browse, path=path)) /
                F(self._add_browse)
            )

        @handle(HistoryBrowse)
        def history_browse(self):
            return self._browse(_.history_info)

        # FIXME seems to drain lazy commit list when cycling
        @handle(HistoryFileBrowse)
        def history_file_browse(self):
            path = Path(
                self.vim.buffer.name if self.msg.path == '' else self.msg.path)
            return self._current_repo_ro // __.relpath(path) / (
                lambda p: self._browse(__.file_history_info(p),
                                       path=Just(p))
            ) | Right(
                Error('current file \'{}\' not in current repo'.format(path)))

        def _io_error(self, exc):
            self.log.caught_exception('nvim io', exc)

        @may_handle(Save)
        def save(self):
            return Commit()

        @property
        def _timestamp(self):
            return datetime.now().isoformat()

        @handle(HistoryBrowseInput)
        def history_browse_input(self):
            return self._current_browse.map(__.send(self.msg))

        @property
        def _current_browse(self):
            return self._browse_for_buffer(self.vim.buffer)

        def _browse_for_buffer(self, buffer):
            return self.state.browse\
                .find(_.buffer.buffer == buffer)\
                .map(_[1])

        @handle(QuitBrowse)
        def quit_browse(self):
            return self._browse_for_buffer(self.msg.buffer)\
                .map(self._remove_browse)

        def _add_browse(self, state: BrowseState):
            browse = Browse(state, self.vim)
            return (
                self._with_browse(self.state.browse + (browse.repo, browse)),
                UnitTask(Task.delay(browse.run))
            )

        def _remove_browse(self, target: Browse):
            return self._with_browse(self.state.browse - target.repo)

        @handle(HistoryPick)
        def pick(self):
            return self._pick_commit\
                .flat_map(lambda a: self._pick_patch(a[0], a[1]))

        @handle(HistoryRevert)
        def revert(self):
            return self._pick_commit\
                .map(lambda a: self._pick_revert(a[0], a[1]))

        @property
        def _pick_commit(self):
            index = try_convert_int(self.msg.index)
            lifter = self._current_repo_ro / _.history_info / _.lift
            return index.ap(lifter).join.product(self.current)

        def _pick_patch(self, commit: CommitInfo, project: Project):
            patch = (
                commit.diff /
                _.revert //
                _.patch
            )
            apply = lambda pat: self._apply_patch(project, pat, commit)
            return patch.map(apply)

        @may
        def _check_pick_status(self, commit, result):
            if result.success:
                self.vim.reload_windows()
                self.log.info('picked {}'.format(commit.num_since))
            else:
                return Error(Plugin.failed_pick_err).pub

        async def _apply_patch(self, project, patch, commit):
            executor = Patch(self.vim)
            result = await executor.patch(project, patch)
            return self._check_pick_status(commit, result)

        async def _pick_revert(self, commit: CommitInfo, project: Project):
            result = await self.executor.revert(project, commit)
            ret = self._check_pick_status(commit, result)
            if not result.success:
                await self.executor.revert_abort(project)
            return ret

        async def _add_commit_coro(self, data):
            project, repo = data
            return await repo.add_commit_all(project, self.executor,
                                             self._timestamp)

        # TODO handle broken repo
        # TODO allow specifying target
        @may_handle(Commit)
        async def commit(self):
            wanted = self.msg.projects
            filt = (lambda p: not wanted or wanted.exists(p.match_ident))
            candidates = self.projects.filter(filt).flat_pair(self._repo_ro)
            results = await gather_sync_flat(candidates, self._add_commit_coro)
            new_repos = results\
                .fold_map(self.state.repos, lambda s: (s.project, s))
            return Just(self._with_sub(self.state.set(repos=new_repos)))

        @may_handle(CommitCurrent)
        def commit_current(self):
            return Commit(*(self.data.current / _.name).to_list)

__all__ = ('Plugin')
