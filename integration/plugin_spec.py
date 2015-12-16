from pathlib import Path
import os
import logging
from contextlib import contextmanager

import sure  # NOQA
from flexmock import flexmock  # NOQA

import neovim  # type: ignore

from tryp import List
import tryp.logging

from tek.test import temp_dir

from proteome.nvim_plugin import ProteomeNvimPlugin
from proteome.project import Project
from proteome.nvim import NvimFacade

from integration._support.base import IntegrationSpec, main_looped


class ProteomePlugin_(IntegrationSpec):

    def setup(self):
        self.cwd = Path.cwd()
        super(ProteomePlugin_, self).setup()
        self.logfile = temp_dir('log') / 'proteome_spec'
        self.logfile.touch()
        tryp.logging.logfile = self.logfile
        tryp.logging.tryp_file_logging(handler_level=logging.WARN)
        argv = ['nvim', '--embed', '-V/dev/null', '-u', 'NONE']
        self.neovim = neovim.attach('child', argv=argv)
        @contextmanager
        def nop_main_loop(self):
            yield
        def mock_async(self, f):
            ret = f(self)
            return ret
        @property
        def mock_proxy(self):
            return self
        NvimFacade.async = mock_async
        NvimFacade.main_event_loop = nop_main_loop
        NvimFacade.proxy = mock_proxy
        self.proteome = ProteomeNvimPlugin(self.neovim)
        self.vim = self.proteome.vim
        self.vim.set_pvar('config_path', str(self.config))
        self.vim.set_pvar('base_dirs', List(str(self.base)))
        self.vim.set_pvar('type_base_dirs', self.type_bases.keymap(str))
        self.vim.set_pvar('history_base', str(self.history_base))
        self.vim.set_pvar('plugins', List('proteome.plugins.history',
                                          'proteome.plugins.ctags'))
        self.pros = self.add_projects(
            ('python', 'pro1'), ('python', 'pro2'), ('vim', 'pro3'))

    def teardown(self):
        super(ProteomePlugin_, self).teardown()
        self.proteome.proteome_quit()
        self.neovim.quit()
        os.chdir(str(self.cwd))
        self.logfile.read_text().splitlines().should.be.empty

    @property
    def _env(self):
        return self.proteome.pro.data

    @property
    def _projects(self):
        return self._env.all_projects

    def _await(self):
        self.proteome.pro.await_state()

    @main_looped
    def add_from_base(self):
        self.proteome.proteome_start()
        self.proteome.pro_add(['python/pro2'])
        self._projects.should.contain(self.pros[1])

    @main_looped
    def ctags(self):
        self.proteome.proteome_start()
        self.pros.foreach(lambda a: self.proteome.pro_add([a.ident]))
        self.proteome.pro_save()
        self.pros.foreach(lambda a: a.tag_file.should.exist)

    @main_looped
    def history(self):
        self.vim.set_pvar('all_projects_history', 1)
        self.proteome.proteome_start()
        self.pros.foreach(lambda a: self.proteome.pro_add([a.ident]))
        self.proteome.post_init()
        self.pros\
            .map(lambda a: self.history_base / a.fqn)\
            .foreach(lambda a: a.should.exist)
        self.pros\
            .foreach(lambda a: (a.root / 'test_file').touch())
        self.proteome.pro_save()
        def check_commit(pro: Project):  # NOQA
            objdir = self.history_base / pro.fqn / 'objects'
            files = list((objdir).iterdir())
            len(files)\
                .should.be.greater_than(2)
        self.pros.foreach(check_commit)

__all__ = ['ProteomePlugin_']
