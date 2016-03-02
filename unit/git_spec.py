from functools import wraps

import sure  # NOQA
from flexmock import flexmock  # NOQA

from fn import _

from proteome.git import History, RepoAdapter

from unit.project_spec import LoaderSpec
from unit._support.async import test_loop

from tryp import Just, __


class Git_(LoaderSpec):

    def with_repo(f):
        @wraps(f)
        def wrapper(self):
            return self.hist.at(self.pro1, lambda r: f(self, r))
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
    def commit_all(self, repo):
        (self.pro1.root / 'test_file').touch()
        r = repo / __.add_commit_all('test')
        (self.rep / 'HEAD').exists().should.be.ok
        self._object_count.should.be.greater_than(2)
        return r

    @with_repo
    def master_with_empty_repo(self, repo):
        return repo / __.to_master()

    @with_repo
    def prev_next(self, repo):
        first = 'first'
        second = 'second'
        file1 = (self.pro1.root / 'test_file_2')
        file2 = (self.pro1.root / 'test_file')
        file1.write_text(first)
        return (
            repo /
            __.add_commit_all(first) @
            (lambda: file2.write_text(first)) /
            __.add_commit_all(second) @
            (lambda: file1.write_text(second)) /
            __.add_commit_all('third') %
            (lambda a: a.history.should.have.length_of(3)) @
            (lambda: file1.read_text().should.equal(second)) /
            __.prev() @
            (lambda: file1.read_text().should.equal(first)) /
            __.next() @
            (lambda: file1.read_text().should.equal(second))
        )

    def _two_commits(self, repo):
        first = 'first'
        second = 'second'
        file1 = (self.pro1.root / 'test_file_2')
        file1.write_text(first)
        return (
            repo /
            __.add_commit_all(first) @
            (lambda: file1.write_text(second)) /
            __.add_commit_all(second)
        )

    @with_repo
    def to_master(self, repo):
        first = 'first'
        second = 'second'
        file1 = (self.pro1.root / 'test_file_2')
        file1.write_text(first)
        return (
            repo /
            __.add_commit_all(first) @
            (lambda: file1.write_text(second)) /
            __.add_commit_all(second) /
            __.prev() @
            (lambda: file1.read_text().should.equal(first)) /
            __.next() @
            (lambda: file1.read_text().should.equal(second))
        )

    @with_repo
    def logg(self, repo):
        def marked(lg, index):
            lg[index][0].should.equal('*')
        first = 'first'
        second = 'second'
        file1 = (self.pro1.root / 'test_file_2')
        file1.write_text(first)
        return (
            repo /
            __.add_commit_all(first) @
            (lambda: file1.write_text(second)) /
            __.add_commit_all(second) %
            (lambda a: marked(a.log_formatted, 0)) /
            __.prev() %
            (lambda a: marked(a.log_formatted, 1))
        )

    @with_repo
    def current(self, repo):
        return (
            self._two_commits(repo) %
            (lambda a: a.current_commit_info.map(_.num).should.contain(0))
        )


class RepoSpec(LoaderSpec):

    def setup(self):
        super().setup()
        git_dir = self.history_base / self.pypro1_name
        self.repo_adapter = RepoAdapter(self.pypro1_root, Just(git_dir))
        self.repo_adapter.repo.should.be.just
        self.repo = self.repo_adapter.repo() | None


class NoCommitRepoSpec(RepoSpec):

    def setup(self):
        super().setup()

    def master(self):
        self.repo.master.should.be.empty

    def commit(self):
        content = 'content'
        test_file = self.pypro1_root / 'test_file'
        test_file.write_text(content)
        self.repo.add_commit_all('test')
        self.repo.master.should_not.be.empty
        self.repo.history.should_not.be.empty

__all__ = ['Git_']
