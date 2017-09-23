from toolz import dicttoolz

from ribosome.machine.message_base import message
from ribosome.machine.transition import may_handle

from proteome.state import ProteomeComponent

Do = message('Do', 'msg')


class Plugin(ProteomeComponent):
    _data_type = dict

    @property
    def title(self):
        return 'test_plug'

    @may_handle(Do)
    def doit(self, env: dict, msg):
        return dicttoolz.merge(env, {msg.msg: msg.msg})


__all__ = ['Plugin']
