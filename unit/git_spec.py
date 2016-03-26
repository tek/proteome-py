from functools import wraps

from fn import _

from proteome.plugins.history import History, HistoryGit

from unit.project_spec import LoaderSpec
from unit._support.async import test_loop

from tryp import __, curried
from tryp.lazy import lazy

from trypnv.nvim import ScratchBuffer


class MockScratchBuffer(ScratchBuffer):

    def __init__(self) -> None:
        pass


class GitSpec(LoaderSpec):

    @lazy
    def executor(self):
        return HistoryGit(self.history_base, self.vim)

    def with_repo(f):
        @wraps(f)
        def wrapper(self):
            with test_loop() as loop:
                @curried
                def commit(msg, repo):
                    coro = repo.add_commit_all(self.pro1, self.executor, msg)
                    return loop.run_until_complete(coro)
                return self.hist.at(self.pro1, lambda r: f(self, r, commit))
        return wrapper

    def setup(self):
        super().setup()
        self.pro1 = self.mk_project('pro1', 'py')
        self.rep = self.history_base / self.pro1.fqn
        self.hist = History(self.history_base)

    @property
    def _object_count(self):
        return len(self.object_files(self.pro1))

    @with_repo
    def commit_all(self, repo, commit):
        (self.pro1.root / 'test_file').touch()
        r = repo / commit('test')
        (self.rep / 'HEAD').exists().should.be.ok
        self._object_count.should.be.greater_than(2)
        return r

    @with_repo
    def master_with_empty_repo(self, repo, _):
        return repo / __.to_master()

    @with_repo
    def prev_next(self, repo, commit):
        first = 'first'
        second = 'second'
        file1 = (self.pro1.root / 'test_file_2')
        file2 = (self.pro1.root / 'test_file')
        file1.write_text(first)
        return (
            repo /
            commit(first) @
            (lambda: file2.write_text(first)) /
            commit(second) @
            (lambda: file1.write_text(second)) /
            commit('third') %
            (lambda a: a.history.should.have.length_of(3)) @
            (lambda: file1.read_text().should.equal(second)) /
            __.prev() @
            (lambda: file1.read_text().should.equal(first)) /
            __.next() @
            (lambda: file1.read_text().should.equal(second))
        )

    def _two_commits(self, repo, commit):
        first = 'first'
        second = 'second'
        file1 = (self.pro1.root / 'test_file_2')
        file1.write_text(first)
        return (
            repo /
            commit(first) @
            (lambda: file1.write_text(second)) /
            commit(second)
        )

    @with_repo
    def to_master(self, repo, commit):
        first = 'first'
        second = 'second'
        file1 = (self.pro1.root / 'test_file_2')
        file1.write_text(first)
        return (
            repo /
            commit(first) @
            (lambda: file1.write_text(second)) /
            commit(second) /
            __.prev() @
            (lambda: file1.read_text().should.equal(first)) /
            __.next() @
            (lambda: file1.read_text().should.equal(second))
        )

    @with_repo
    def repo_log(self, repo, commit):
        def marked(lg, index):
            lg[index][0].should.equal('*')
        first = 'first'
        second = 'second'
        file1 = (self.pro1.root / 'test_file_2')
        file1.write_text(first)
        return (
            repo /
            commit(first) @
            (lambda: file1.write_text(second)) /
            commit(second) %
            (lambda a: marked(a.log_formatted, 0)) /
            __.prev() %
            (lambda a: marked(a.log_formatted, 1))
        )

    @with_repo
    def file_browse(self, repo, commit):
        def check(repo):
            diffs = (repo.file_history_info(file1).drain /
                     __.browse_format(True, repo.relpath(file1) / str))
            diffs.should.have.length_of(2)
            diffs[0].find(lambda a: name3 in a).should.be.empty
        first = 'first'
        second = 'second'
        third = 'third'
        file1 = (self.pro1.root / 'test_file_2')
        name3 = 'test_file_3'
        file2 = (self.pro1.root / name3)
        file1.write_text(first)
        return (
            repo /
            commit(first) @
            (lambda: file1.write_text(second)) @
            (lambda: file2.write_text(first)) /
            commit(second) @
            (lambda: file2.write_text(third)) /
            commit(third) %
            check
        )

    @with_repo
    def current(self, repo, commit):
        return (
            self._two_commits(repo, commit) %
            (lambda a: a.current_commit_info.map(_.num).should.contain(0))
        )

__all__ = ('GitSpec',)
