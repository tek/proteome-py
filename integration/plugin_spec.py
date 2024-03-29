import logging
from contextlib import contextmanager
import json
import asyncio

import neovim

from amino import List, Map, Just
from amino.test.spec_spec import later
import amino.logging

from amino.test import temp_dir

import ribosome
from ribosome.test.integration.spec import main_looped
from ribosome.nvim import NvimFacade

from proteome import ProteomeNvimPlugin
from proteome.project import Project

from integration._support.base import ProteomeIntegrationSpec


@contextmanager
def _nop_main_loop(self):
    yield


def _mock_async(self, f):
    ret = f(self)
    return ret


def _mock_proxy(self):
    return self


class ProteomePlugin_(ProteomeIntegrationSpec):

    def setup(self):
        ribosome.in_vim = False
        super().setup()
        self.logfile = temp_dir('log') / 'proteome_spec'
        self.vimlog = temp_dir('log') / 'vim'
        self.logfile.touch()
        amino.logging.logfile = self.logfile
        amino.logging.amino_root_file_logging(level=logging.WARN)
        argv = ['nvim', '--embed', '-V{}'.format(self.vimlog), '-u', 'NONE']
        self.neovim = neovim.attach('child', argv=argv)
        NvimFacade.async = _mock_async
        NvimFacade.main_event_loop = _nop_main_loop
        NvimFacade.proxy = property(_mock_proxy)
        NvimFacade.clean = lambda self: True
        self.proteome = ProteomeNvimPlugin(self.neovim)
        self.vim = self.proteome.vim
        self.vim.vars.set_p('config_path', str(self.config))
        self.vim.vars.set_p('base_dirs', List(str(self.base)))
        self.vim.vars.set_p('type_base_dirs', self.type_bases.keymap(str))
        self.vim.vars.set_p('history_base', str(self.history_base))
        self.vim.vars.set_p('components', List('proteome.components.history',
                                          'proteome.components.ctags',
                                          'proteome.components.config',
                                          'proteome.components.unite',
                                          ))
        self.pros = self.add_projects(
            ('python', 'pro1'), ('python', 'pro2'), ('vim', 'pro3'))

    def _post_startup(self):
        self.proteome.proteome_post_startup()

    def teardown(self):
        super().teardown()
        self.proteome.proteome_quit()
        self.neovim.quit()
        self.logfile.read_text().splitlines().should.be.empty

    @property
    def _env(self):
        return self.proteome.pro.data

    @property
    def _projects(self):
        return self._env.all_projects

    def _await(self):
        self.proteome.pro.await_state()

    def add_by_ident(self):
        self.proteome.stage_1()
        self.proteome.pro_add(['python/pro2'])
        self._await()
        self._projects.should.contain(self.pros[1])

    def complete_project(self):
        id1 = 'python/pro2'
        self.proteome.stage_1()
        self.proteome.pro_add([id1])
        self._await()
        idents = self.proteome.pro_complete_projects(['', '', ''])
        set(idents).should.equal(set(['main', id1]))

    def complete_addable(self):
        def check(pre, ident):
            idents = self.proteome.pro_complete_addable_projects([pre, '', ''])
            set(idents).should.equal(set(ident))
        pro4n = 'pro4'
        pro4 = '{}/{}'.format(self.type1, pro4n)
        temp_dir(self.type1_base / pro4n)
        self.proteome.stage_1()
        self._await()
        check('', ['python/pro1', 'python/pro2', 'vim/pro3', pro4])
        check('py', ['python/pro1', 'python/pro2'])
        check('type1', [pro4])

    def add_by_params(self):
        tpe = 'ptype'
        name = 'pname'
        ident = '{}/{}'.format(tpe, name)
        root = temp_dir('plugin/from_params')
        params = Map(
            root=str(root),
            history=False,
        )
        self.proteome.stage_1()
        self.proteome.pro_add([ident] + json.dumps(params).split(' '))
        self._await()
        self._projects.last.should.contain(Project.of(name, root, Just(tpe)))

    def remove_by_ident(self):
        self.proteome.stage_1()
        self.proteome.proteome_post_startup()
        self._await()
        self.proteome.pro_add(['python/pro2'])
        later(lambda: self._env.current_index.should.equal(1))
        self.proteome.pro_remove(['python/pro2'])
        later(lambda: self._env.current_index.should.equal(0))

    def ctags(self):
        self.proteome.stage_1()
        self.pros.foreach(lambda a: self.proteome.pro_add([a.ident]))
        self._await()
        self.proteome.pro_save()
        self._await()
        later(lambda: self.pros.foreach(lambda a: a.tag_file.should.exist))

    def history(self):
        def check_commit(pro: Project):
            l = len(self.object_files(pro))
            l.should.be.greater_than(2)  # type: ignore
        self.vim.vars.set_p('all_projects_history', 1)
        self.proteome.stage_1()
        self.pros.foreach(lambda a: self.proteome.pro_add([a.ident]))
        self._post_startup()
        self._await()
        self.pros\
            .map(lambda a: self.history_base / a.fqn)\
            .foreach(lambda a: a.should.exist)
        self.pros\
            .foreach(lambda a: (a.root / 'test_file').touch())
        self.proteome.pro_save()
        self._await()
        self.pros.foreach(check_commit)

__all__ = ['ProteomePlugin_']
