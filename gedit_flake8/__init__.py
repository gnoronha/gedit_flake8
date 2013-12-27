#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""gedit-flake8 : A plugin for gedit
   to display error and warning from flake8."""

__author__ = "Benoît HERVIER"
__copyright__ = "Copyright 2012 " + __author__
__license__ = "GPLv3"
__version__ = "0.6.2"
__maintainer__ = "Benoît HERVIER"
__email__ = "khertan@khertan.net"
__status__ = "Beta"

try:
    from gi.repository import GObject, Gedit, Gtk
except ImportError as err:
    print('GEdit-Flake8 needs to be launched by GEdit 3')
    print(err)

import codecs
import re
from subprocess import Popen, PIPE
import threading

from .renderer import ErrorRenderer, ErrorType

GObject.threads_init()


class _IdleObject(GObject.Object):
    """
    Override gobject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        GObject.Object.__init__(self)

    def emit(self, *args):
        GObject.idle_add(GObject.Object.emit, self, *args)


class Message(object):

    def __init__(self, document, lineno, column, message):

        self._doc = document

        self._lineno = lineno
        self._column = column
        self._message = message

        self._start_iter = None
        self._end_iter = None

        if message.startswith('E'):
            self._type = ErrorType.ERROR

        elif message.startswith('W'):
            self._type = ErrorType.WARNING

        else:
            self._type = ErrorType.INFO

    def setWordBounds(self, start, end):
        self._start_iter = start
        self._end_iter = end

    doc = property(lambda self: self.__doc)

    lineno = property(lambda self: self._lineno)
    column = property(lambda self: self._lineno)
    message = property(lambda self: self._message)
    error_type = property(lambda self: self._type)

    start = property(lambda self: self._start_iter)
    end = property(lambda self: self._end_iter)


class Worker(threading.Thread, _IdleObject):
    __gsignals__ = {
        "completed": (
            GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []), }

    def __init__(self, document, error_renderer):
        self.document = document
        threading.Thread.__init__(self)
        _IdleObject.__init__(self)

        try:
            self._encoding = self.document.get_encoding().get_charset()
        except Exception:
            self._encoding = 'utf-8'
        self._path = '/tmp/gedit_flake8.py'
        start, end = self.document.get_bounds()

        self._contents = str(self.document.get_text(start, end,
                                                    include_hidden_chars=True))

        self.error_renderer = error_renderer
        self._errors = []
        self._file_context = {}
        self.cancelled = False

    def run(self):
        errors = []

        with codecs.open(self._path, 'w', encoding=self._encoding) as fh:
            fh.write(self._contents)
        del self._contents

        stdout, stderr = Popen(['flake8', self._path],
                               stdout=PIPE, stderr=PIPE).communicate()
        output = stdout if stdout else stderr

        line_format = re.compile(
            '(?P<path>[^:]+):(?P<line>\d+):'
            + '(?P<character>\d+:)?\s(?P<message>.*$)')

        if not output:
            if not self.cancelled:
                self.emit("completed")
            return

        file_context = self._file_context
        for line in output.splitlines():
            line = line.decode('utf8')
            m = line_format.match(line)
            if not m:
                continue
            groups = m.groupdict()
            line_number = int(groups['line'])
            if groups['character']:
                err = Message(self.document,
                              line_number,
                              int(groups['character'].strip(':')),
                              groups['message'],)
            else:
                err = Message(self.document,
                              line_number,
                              0,
                              groups['message'],)
            errors.append(err)
            file_context[line_number] = err

        self._errors = errors

        if not self.cancelled:
            self.emit("completed")


class Flake8Plugin(GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "Flake8"

    view = GObject.property(type=Gedit.View)
    _errors = []
    _worker = None

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        document = self.view.get_buffer()

        self.gutter = self.view.get_gutter(Gtk.TextWindowType.LEFT)

        self.error_renderer = ErrorRenderer()

        document.connect('loaded', self.analyse)
        document.connect('saved', self.analyse)
        document.connect_after('changed', self.analyse)

    def do_deactivate(self):
        self._errors = None

        self.gutter.remove(self.error_renderer)
        self.error_renderer.set_file_context({})

    def completedCb(self, *userData):
        if self._worker._file_context:
            self.error_renderer.set_file_context(self._worker._file_context)
            if not self.error_renderer.get_view():
                self.gutter.insert(self.error_renderer, 40)
        else:
            self.error_renderer.set_file_context({})
            self.gutter.remove(self.error_renderer)

        self._errors = self._worker._errors
        self._worker = None

    def analyse(self, document, option=None):
        """Launch a process and populate vars"""
        if document is None:
            return True
        try:
            if document.get_language().get_name() != 'Python':
                return True
        except AttributeError:
            return True

        if self._worker is not None:
            self._worker.cancelled = True
        self._worker = Worker(document, self.error_renderer)
        self._worker.connect("completed", self.completedCb)
        self._worker.start()

