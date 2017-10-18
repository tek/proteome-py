from ribosome.machine.message_base import message, json_message

Add = message('Add', 'project')
RemoveByIdent = message('RemoveByIdent', 'ident')
Create = message('Create', 'name', 'root')
Next = message('Next')
Prev = message('Prev')
SetProject = message('SetProject', 'ident')
SetProjectIdent = message('SetProjectIdent', 'ident')
SetProjectIndex = message('SetProjectIndex', 'index')
SwitchRoot = message('SwitchRoot', opt_fields=(('notify', True),))
Save = message('Save')
Load = message('Load')
Added = message('Added', 'project')
Removed = message('Removed', 'project')
ProjectChanged = message('ProjectChanged', 'project')
BufEnter = message('BufEnter', 'buffer')
Initialized = message('Initialized')
MainAdded = message('MainAdded')
Show = message('Show', varargs='names')
AddByParams = json_message('AddByParams', 'ident')
CloneRepo = json_message('CloneRepo', 'uri')

__all__ = ('Add', 'RemoveByIdent', 'Create', 'Next', 'Prev', 'SetProject', 'SetProjectIdent', 'SetProjectIndex',
           'SwitchRoot', 'Save', 'Load', 'Added', 'Removed', 'ProjectChanged', 'BufEnter', 'Initialized', 'MainAdded',
           'Show', 'AddByParams', 'CloneRepo')
