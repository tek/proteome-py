from ribosome.machine import message

Commit = message('Commit', varargs='projects')
CommitCurrent = message('CommitCurrent')
HistorySwitch = message('HistorySwitch', 'index')
HistorySwitchFile = message('HistorySwitchFile', 'path', 'id')
HistoryPrev = message('HistoryPrev')
HistoryNext = message('HistoryNext')
HistoryBufferPrev = message('HistoryBufferPrev')
HistoryBufferNext = message('HistoryBufferNext')
HistoryStatus = message('HistoryStatus')
HistoryLog = message('HistoryLog')
HistoryBrowse = message('HistoryBrowse')
HistoryFileBrowse = message('HistoryBrowse', opt_fields=(('path', ''),))
HistoryBrowseInput = message('HistoryBrowseInput', 'keyseq')
HistoryPick = message('HistoryPick', 'index')
HistoryRevert = message('HistoryRevert', 'index')
Redraw = message('Redraw')
QuitBrowse = message('QuitBrowse', 'buffer')
ExecPick = message('ExecPick', 'commit', 'executor', 'status')
RevertAbort = message('ExecPick', 'project', 'executor', 'status')
