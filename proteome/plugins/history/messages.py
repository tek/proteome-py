from trypnv.machine import message

Commit = message('Commit')
HistorySwitch = message('HistorySwitch', 'index')
HistoryPrev = message('HistoryPrev')
HistoryNext = message('HistoryNext')
HistoryBufferPrev = message('HistoryBufferPrev')
HistoryBufferNext = message('HistoryBufferNext')
HistoryStatus = message('HistoryStatus')
HistoryLog = message('HistoryLog')
HistoryBrowse = message('HistoryBrowse')
HistoryBrowseInput = message('HistoryBrowseInput', 'keyseq')
Redraw = message('Redraw')
QuitBrowse = message('QuitBrowse', 'buffer')
