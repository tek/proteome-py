from pathlib import Path  # type: ignore
from functools import reduce  # type: ignore
import importlib

from fn import _  # type: ignore

from tryp import List, may, Map

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
            bases: List[Path],
            type_bases: Map[Path, List[str]],
    ) -> None:
        self._config_path = config_path
        self._bases = bases
        self._type_bases = type_bases
        core = 'proteome.plugins.core'
        super(Proteome, self).__init__(vim)
        self.plugins = (plugins + [core]).flat_map(self.start_plugin)

    @may
    def start_plugin(self, path: str):
        try:
            mod = importlib.import_module(path)
        except ImportError as e:
            msg = 'invalid proteome plugin module "{}": {}'.format(path, e)
            self.log.error(msg)
        else:
            if hasattr(mod, 'Plugin'):
                name = path.split('.')[-1]
                return getattr(mod, 'Plugin')(name, self.vim)

    def init(self):
        return Env(  # type: ignore
            config_path=self._config_path,
            bases=self._bases,
            type_bases=self._type_bases,
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
        cmd = plug.flat_map(lambda a: a.command(cmd_name, List(args)))
        plug.zip(cmd).smap(self.send_plug_command)

    def send_plug_command(self, plug, msg):
        self.log.debug('sending command {} to plugin {}'.format(msg,
                                                                plug.name))
        self._data = plug.process(self._data, msg)

__all__ = ['Proteome']
