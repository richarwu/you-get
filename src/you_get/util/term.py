#!/usr/bin/env python
import shutil
import sys

def get_terminal_size():
    """Get (width, height) of the current terminal."""
    if int(sys.version[2]) >= 3:
        term_size = shutil.get_terminal_size((80, 40))
        return term_size[1], term_size[0]
    try:
        import fcntl, termios, struct # fcntl module only available on Unix
        return struct.unpack('hh', fcntl.ioctl(1, termios.TIOCGWINSZ, '1234'))
    except Exception:
#fallback here for windows and py version < 3.3. quite rare
#getting terminal size from winapi GetConsoleScreenBufferInfo is easy
#but I doubt it worths the effort
        return (40, 80-10)
