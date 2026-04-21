import os
import sys
import win32api
import win32con
import win32process

# sometimes stuff just cuts out on my machine so
def _elevate_process_priority():
    try:
        sys.getwindowsversion()
    except AttributeError:
        is_windows = False
    else:
        is_windows = True

    if is_windows:
        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(handle, win32process.ABOVE_NORMAL_PRIORITY_CLASS)

    else:
        os.nice(1)