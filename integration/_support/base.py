from pathlib import Path
from threading import Thread
import asyncio
from functools import wraps

from tek.test import fixture_path, temp_dir  # type: ignore

from tryp import List, Map, Just

from integration._support.spec import Spec

from proteome.project import Project


class IntegrationSpec(Spec):

    def setup(self, *a, **kw):
        super(IntegrationSpec, self).setup(*a, **kw)
        self.config = fixture_path('conf')
        self.base = temp_dir('projects', 'base')
        self.type1_base = temp_dir('projects', 'type1')
        self.type_bases = Map({self.type1_base: List('type1')})
        self.history_base = temp_dir('history')

    def mk_project(self, tpe, name):
        root = temp_dir(str(self.base / tpe / name))
        return Project(name, Path(root), tpe=Just(tpe))

    def add_projects(self, *pros):
        return List(*pros).smap(self.mk_project)


def main_looped(fun):
    @wraps(fun)
    def wrapper(self):
        loop = asyncio.get_event_loop()
        done = asyncio.Future()
        def runner():
            fun(self)
            loop.call_soon_threadsafe(lambda: done.set_result(True))
        Thread(target=runner).start()
        loop.run_until_complete(done)
    return wrapper

__all__ = ['IntegrationSpec']
