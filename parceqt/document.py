# -*- coding: utf-8 -*-
#
# This file is part of the parce-qt Python package.
#
# Copyright © 2020 by Wilbert Berendsen <info@wilbertberendsen.nl>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""
This module implements a Document encapsulating a QTextDocument.

It is not needed to store the Document itself, it is only used
to modify the QTextDocument through the parce.Document API.

We do not ourself retokenize the text, that is done by a TreeBuilder
that is automatically connected to the document.

"""

from PyQt5.QtCore import QMimeData
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication

import parce.treedocument
import parce.document

from . import treebuilder


class Document(
    parce.treedocument.TreeDocumentMixin, parce.document.AbstractDocument):
    """Document accesses a QTextDocument via the parce.Document API.

    There is no need to store this object, it is only used to access and
    modify the contents of a QTextDocument. Example::

        d = Document(doc)   # where doc is an existing QTextDocument
        with d:
            d[5:5] = 'some text'

    This is useful when you have written code that manipulates text files based
    on the tokenized tree via the parce.Document API, you can use the same code
    to manipulate QTextDocuments in an interactive session.

    As opposed to parce.Document, this Document class does not update the token
    tree by itself, that is handled by the TreeBuilder that does its work in
    the background.

    """
    def __init__(self, document, builder=None):
        """Initialize with QTextDocument."""
        parce.document.AbstractDocument.__init__(self)
        if not builder:
            builder = treebuilder.TreeBuilder.instance(document)
        parce.treedocument.TreeDocumentMixin.__init__(self, builder)
        self._document = document

    def document(self):
        """Return our QTextDocument."""
        return self._document

    def text(self):
        """Reimplemented to get the text from the QTextDocument."""
        return self.document().toPlainText()

    def __len__(self):
        """Reimplemented to return the length of the text in the QTextDocument."""
        # see https://bugreports.qt.io/browse/QTBUG-4841
        return self.document().characterCount() - 1

    def _update_contents(self):
        """Apply the changes to our QTextDocument."""
        c = QTextCursor(self.document())
        c.beginEditBlock()
        for start, end, text in reversed(self._changes):
            c.setPosition(end)
            if start != end:
                c.setPosition(start, QTextCursor.KeepAnchor)
            c.insertText(text)
        c.endEditBlock()

    def _get_contents(self, start, end):
        """Reimplemented to get a fragment of our text.

        This is faster than getting the whole text and using Python to slice it.

        """
        c = QTextCursor(self.document())
        c.setPosition(end)
        c.setPosition(start, QTextCursor.KeepAnchor)
        return c.selection().toPlainText()

    def contents_changed(self, start, removed, added):
        """Reimplemented to do nothing, it is already handled by TreeBuilder."""
        pass

    def find_start_of_block(self, position):
        """Reimplemented to use QTextDocument's TextBlock."""
        block = self.document().findBlock(position)
        if not block.isValid():
            block = self.document().lastBlock()
        return block.position()

    def find_end_of_block(self, position):
        """Reimplemented to use QTextDocument's TextBlock."""
        block = self.document().findBlock(position)
        if not block.isValid():
            block = self.document().lastBlock()
        return block.position() + block.length() - 1


class Cursor(parce.document.Cursor):
    """A cursor with a textCursor() method to return a QTextCursor.

    Only use this Cursor with parceqt.Document.

    """
    def textCursor(self):
        """Return a QTextCursor for our document with the same position and
        selection.

        (This method uses the Qt camelCase naming convention.)

        """
        c = QTextCursor(self.document().document())
        if self.end is None:
            c.movePosition(QTextCursor.End)
        else:
            c.setPosition(self.end)
        c.setPosition(self.start, QTextCursor.KeepAnchor)
        return c

    def html(self):
        """Return the selected range as HTML.

        Uses the same theme(s) as the highlighter (if active).

        """
        from . import highlighter, treebuilder
        from parce.out.html import HtmlFormatter
        formatter = HtmlFormatter()
        b = treebuilder.TreeBuilder.get_instance(self.document().document())
        if b:
            h = highlighter.SyntaxHighlighter.get_instance(b)
            if h and h.formatter():
                formatter.copy_themes(h.formatter())
        return formatter.full_html(self)

    def copy_html(self):
        """Copy the selected range as HTML to the Qt clipboard."""
        data = QMimeData()
        data.setHtml(self.html())
        QApplication.clipboard().setMimeData(data)


