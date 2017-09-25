from ribosome.machine.message_base import Message


class UniteMessage(Message, varargs='unite_args'):
    pass


class UniteSelectAdd(UniteMessage):
    pass


class UniteSelectAddAll(UniteMessage):
    pass


class UniteProjects(UniteMessage):
    pass


class UniteNames():
    addable_candidates = '_proteome_unite_addable'
    all_addable_candidates = '_proteome_unite_all_addable'
    projects_candidates = '_proteome_unite_projects'

    add_project = '_proteome_unite_add_project'
    delete_project = '_proteome_unite_delete_project'
    activate_project = '_proteome_unite_activate_project'

    addable = 'proteome_addable'
    all_addable = 'proteome_all_addable'
    projects = 'proteome_projects'
    project = 'proteome_project'

__all__ = ('UniteNames', 'UniteSelectAdd', 'UniteSelectAddAll', 'UniteProjects')
