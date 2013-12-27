# -*- coding: utf-8 -*-

#  Copyright (C) 2013 - Ignacio Casal Quinteiro
#  Copyright (C) 2013 - Gustavo Noronha Silva <gns@gnome.org>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330,
#  Boston, MA 02111-1307, USA.

import math
from gi.repository import Gdk, Gtk, GtkSource


class ErrorType:
    (NONE,
     INFO,
     WARNING,
     ERROR) = range(4)


class ErrorRenderer(GtkSource.GutterRenderer):

    backgrounds = {}
    backgrounds[ErrorType.INFO] = Gdk.RGBA()
    backgrounds[ErrorType.WARNING] = Gdk.RGBA()
    backgrounds[ErrorType.ERROR] = Gdk.RGBA()
    backgrounds[ErrorType.INFO].parse("#2D10E6")
    backgrounds[ErrorType.WARNING].parse("#CDD415")
    backgrounds[ErrorType.ERROR].parse("#D4153E")

    def __init__(self):
        GtkSource.GutterRenderer.__init__(self)

        self.set_size(8)
        self.set_padding(3, 0)

        self.file_context = {}
        self.tooltip = None
        self.tooltip_line = 0

    def do_draw(self, cr, bg_area, cell_area, start, end, state):
        GtkSource.GutterRenderer.do_draw(self, cr, bg_area, cell_area,
                                         start, end, state)

        line_context = self.file_context.get(start.get_line() + 1, None)
        if line_context is None or line_context.error_type == ErrorType.NONE:
            return

        background = self.backgrounds[line_context.error_type]

        Gdk.cairo_set_source_rgba(cr, background)
        cr.translate(cell_area.x + cell_area.width / 2.,
                     cell_area.y + cell_area.height / 2.)
        cr.scale(cell_area.width / 2., cell_area.height / 2.)
        cr.arc(0., 0., 1., 0, 2 * math.pi)
        cr.fill()

    def do_query_tooltip(self, it, area, x, y, tooltip):
        line = it.get_line() + 1

        line_context = self.file_context.get(line, None)
        if line_context is None:
            return False

        tooltip_buffer = Gtk.TextBuffer()
        tooltip_view = Gtk.TextView.new_with_buffer(tooltip_buffer)

        # Fix some styling issues
        tooltip_view.set_border_width(4)
        tooltip_view.set_cursor_visible(False)

        tooltip_buffer.set_text(line_context.message)

        # Avoid having to create the tooltip multiple times
        self.tooltip = tooltip_view
        self.tooltip_line = line

        tooltip.set_custom(tooltip_view)
        return True

    def set_file_context(self, file_context):
        self.file_context = file_context
        self.tooltip = None
        self.tooltip_line = 0

        self.queue_draw()

# ex:ts=4:et:
