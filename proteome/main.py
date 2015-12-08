from pathlib import Path  # type: ignore
from functools import reduce  # type: ignore
import importlib

from fn import _  # type: ignore

from tryp import List, may

from trypnv import Log

from proteome.nvim import NvimFacade
from proteome.env import Env
from proteome.state import ProteomeState
from proteome.project import Projects


class Proteome(ProteomeState):

    def __init__(
            self,
            vim: NvimFacade,
            config_path: Path,
            plugins: List[str],
            bases: List[Path]
    ) -> None:
        self._config_path = config_path
        self._bases = bases
        core = 'proteome.plugins.core'
        super(Proteome, self).__init__(vim)
        self.plugins = (plugins + [core]).flat_map(self.start_plugin)

    @may
    def start_plugin(self, path: str):
        try:
            mod = importlib.import_module(path)
        except ImportError as e:
            msg = 'invalid proteome plugin module "{}": {}'.format(path, e)
            Log.error(msg)
        else:
            if hasattr(mod, 'Plugin'):
                name = path.split('.')[-1]
                return getattr(mod, 'Plugin')(name, self.vim)

    def init(self):
        return Env(  # type: ignore
            config_path=self._config_path,
            bases=self._bases,
            projects=Projects()
        )

    @property
    def projects(self):
        return self.env.projects

    @may
    def unhandled(self, env, msg):
        return reduce(lambda e, plug: plug.process(e, msg), self.plugins, env)

    def plugin(self, name):
        return self.plugins.find(_.name == name)

    def plug_command(self, plug_name: str, cmd_name: str, args: list):
        plug = self.plugin(plug_name)
        plug.zip(plug.map(lambda a: a.command(cmd_name, List(args))))\
            .smap(self.send_plug_command)

    def send_plug_command(self, plug, msg):
        self._data = plug.process(self._data, msg)

__all__ = ['Proteome']