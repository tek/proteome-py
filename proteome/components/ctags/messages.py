from ribosome.machine.message_base import message

Gen = message('Gen', 'project')
GenAll = message('GenAll')
Kill = message('Kill')
CurrentBuffer = message('CurrentBuffer')

__all__ = ('Gen', 'GenAll', 'Kill', 'CurrentBuffer')
