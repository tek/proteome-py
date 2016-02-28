from pathlib import Path
from datetime import datetime

from fn import _, F  # type: ignore

from tryp.lazy import lazy
from tryp import Map, __, Just, Empty, may, List, Maybe
from tryp.util.numeric import try_convert_int

from trypnv.machine import (may_handle, message, handle, IO)  # type: ignore
from trypnv.machine import Error  # type: ignore
from trypnv.record import field, list_field, dfield, Record
from trypnv.nvim import ScratchBuilder, ScratchBuffer

from proteome.state import ProteomeComponent, ProteomeTransitions
from proteome.git import (History, HistoryT, HistoryState, Repo, CommitInfo,
                          HistoryGit, pygit_working)
from proteome.plugins.core import Save, StageIV
from proteome.logging import Logging
from proteome.project import Project
from proteome.plugins.history.messages import (HistoryPrev, HistoryNext,
                                               HistoryStatus, HistoryLog,
                                               HistoryBrowse,
                                               HistoryBrowseInput,
                                               HistorySwitch, Redraw,
                                               QuitBrowse, Commit,
                                               HistoryBufferNext,
                                               HistoryBufferPrev, HistoryPick,
                                               HistoryRevert)
from proteome.plugins.history.patch import Patch


class BrowseState(Record):
    repo = field(Repo)
    current = field(int)
    commits = list_field()
    buffer = field(ScratchBuffer)
    selected = dfield(0)

Init = message('Init')


class BrowseMachine(ProteomeComponent):
    _data_type = BrowseState

    class Transitions(ProteomeTransitions):

        @property
        def buffer(self):
            return self.data.buffer.proxy

        @property
        def content(self):
            sel = self.data.selected
            return List.wrap(enumerate(self.data.commits[:sel + 20]))\
                .flat_smap(lambda i, a: a.browse_format(i == sel))

        def _create_mappings(self):
            List('j', 'k', 's', 'p', 'r').foreach(self._create_mapping)
            self._create_mapping('<cr>', to='%CR%')

        def _create_mapping(self, keyseq, mode='n', to=None):
            to_seq = Maybe(to) | keyseq
            raw = self.buffer.buffer
            cmd = ':ProHistoryBrowseInput {}<cr>'.format(to_seq)
            raw.nmap(keyseq, cmd)

        def _configure_appearance(self):
            self.buffer.set_options('filetype', 'diff')
            self.buffer.set_options('syntax', 'diff')
            self.buffer.window.set_optionb('cursorline', True)
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
            })
            return handlers.get(self.msg.keyseq).flat_map(lambda f: f())

        def _down(self):
            return self._select_diff(1)

        def _up(self):
            return self._select_diff(-1)

        @may
        def _select_diff(self, diff):
            index = self.data.selected + diff
            if 0 <= index < len(self.data.commits):
                return self.data.set(selected=index), Redraw()

        @may
        def _switch(self):
            q = QuitBrowse(self.buffer)
            return (HistorySwitch(self.data.selected).pub, q, q.pub)

        @may_handle(QuitBrowse)
        def quit(self):
            if self.msg.buffer == self.buffer:
                self._close_tab()

        def _close_tab(self):
            self.buffer.tab.close()

        def _pick(self):
            return self._pick_commit(HistoryPick)

        def _revert(self):
            return self._pick_commit(HistoryRevert)

        @may
        def _pick_commit(self, tpe):
            q = QuitBrowse(self.buffer)
            return (tpe(self.data.selected).pub, q, q.pub)


class Browse(Logging):

    def __init__(self, state: BrowseState, vim) -> None:
        self.state = state
        self.machine = BrowseMachine('history_browse', vim)

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
        return self.vim.pdir('history_base').get_or_else(Path('/dev/null'))

    class Transitions(ProteomeTransitions):

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
            new_state = self.projects.fold_left(self.history_t)(g).state
            return self._with_sub(new_state)

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

        @may_handle(StageIV)
        def stage_4(self):
            if pygit_working:
                return self._with_repos(lambda a: Just(a.state))
            else:
                msg = ('proteome/history failure: Install the libgit2 system'
                       ' package and pygit2 in each virtualenv')
                return Error(msg).pub

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
                .map(__.index)\
                .flat_map(self._switch)

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
            self._with_current_repo(_ / log_status)

        @may_handle(HistoryLog)
        def history_log(self):
            self._with_current_repo(
                _ % (lambda r: self.vim.multi_line_info(r.log_formatted))
            )

        @handle(HistoryBrowse)
        def history_browse(self):
            def f(repo):
                commits = repo.history_info
                return ScratchBuilder().build.unsafe_perform_io(self.vim)\
                    .leffect(self._io_error)\
                    .map(lambda a: BrowseState(repo=repo, current=0,
                                               commits=commits, buffer=a))
            return self._current_repo_ro\
                .flat_map(f)\
                .map(self._add_browse)

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
                IO(browse.run)
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
            return index.ap(lifter).flatten.product(self.current)

        def _pick_patch(self, commit: CommitInfo, project: Project):
            patch = (
                commit.diff /
                _.revert //
                _.patch
            )
            apply = lambda pat: self._apply_patch(project, pat, commit)
            return patch.map(apply)

        async def _apply_patch(self, project, patch, commit):
            executor = Patch(self.vim)
            result = await executor.patch(project, patch)
            return self._check_pick_status(commit, executor, result)

        async def _pick_revert(self, commit: CommitInfo, project: Project):
            executor = HistoryGit(self.machine.base, self.vim)
            result = await executor.revert(project, commit)
            ret = self._check_pick_status(commit, executor, result)
            if not result.success:
                await executor.revert_abort(project)
            return ret

        @may
        def _check_pick_status(self, commit, executor, result):
            if result.success:
                self.vim.reload_windows()
                self.log.info('picked {}'.format(commit.num_since))
            else:
                return Error(Plugin.failed_pick_err).pub

__all__ = ('Commit', 'Plugin', 'HistoryPrev', 'HistoryNext',
           'HistoryBufferPrev', 'HistoryBufferNext', 'HistorySwitch',
           'HistoryPick', 'HistoryRevert')
