from pathlib import Path
import os
import logging
from contextlib import contextmanager
import json

import sure  # NOQA
from flexmock import flexmock  # NOQA

import neovim  # type: ignore

from tryp import List, Map, Just
import tryp.logging

from tek.test import temp_dir

from proteome.nvim_plugin import ProteomeNvimPlugin
from proteome.project import Project
from proteome.nvim import NvimFacade

from integration._support.base import IntegrationSpec, main_looped


@contextmanager
def _nop_main_loop(self):
    yield


def _mock_async(self, f):
    ret = f(self)
    return ret


@property
def _mock_proxy(self):
    return self


class ProteomePlugin_(IntegrationSpec):

    def setup(self):
        self.cwd = Path.cwd()
        super().setup()
        self.logfile = temp_dir('log') / 'proteome_spec'
        self.vimlog = temp_dir('log') / 'vim'
        self.logfile.touch()
        tryp.logging.logfile = self.logfile
        tryp.logging.tryp_file_logging(handler_level=logging.WARN)
        argv = ['nvim', '--embed', '-V{}'.format(self.vimlog), '-u', 'NONE']
        self.neovim = neovim.attach('child', argv=argv)
        NvimFacade.async = _mock_async
        NvimFacade.main_event_loop = _nop_main_loop
        NvimFacade.proxy = _mock_proxy
        NvimFacade.clean = lambda self: True
        self.proteome = ProteomeNvimPlugin(self.neovim)
        self.vim = self.proteome.vim
        self.vim.set_pvar('config_path', str(self.config))
        self.vim.set_pvar('base_dirs', List(str(self.base)))
        self.vim.set_pvar('type_base_dirs', self.type_bases.keymap(str))
        self.vim.set_pvar('history_base', str(self.history_base))
        self.vim.set_pvar('plugins', List('proteome.plugins.history',
                                          'proteome.plugins.ctags',
                                          'proteome.plugins.config',
                                          ))
        self.pros = self.add_projects(
            ('python', 'pro1'), ('python', 'pro2'), ('vim', 'pro3'))

    def _post_startup(self):
        self.proteome.proteome_post_startup()

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
        self._await()
        self._projects.should.contain(self.pros[1])

    @main_looped
    def add_from_params(self):
        tpe = 'ptype'
        name = 'pname'
        ident = '{}/{}'.format(tpe, name)
        root = temp_dir('plugin/from_params')
        params = Map(
            root=str(root),
            history=False
        )
        self.proteome.proteome_start()
        self.proteome.pro_add([ident] + json.dumps(params).split(' '))
        self._await()
        self._projects.last.should.contain(Project.of(name, root, Just(tpe)))

    @main_looped
    def ctags(self):
        self.proteome.proteome_start()
        self.pros.foreach(lambda a: self.proteome.pro_add([a.ident]))
        self._await()
        self.proteome.pro_save()
        self._await()
        self.pros.foreach(lambda a: a.tag_file.should.exist)

    @main_looped
    def history(self):
        def check_commit(pro: Project):
            len(self.object_files(pro))\
                .should.be.greater_than(2)
        self.vim.set_pvar('all_projects_history', 1)
        self.proteome.proteome_start()
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
