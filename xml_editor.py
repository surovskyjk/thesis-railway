# XML viewer with syntax highlighting and code folding built on QPlainTextEdit
import re

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QSyntaxHighlighter,
                           QTextCharFormat, QTextCursor)
from PySide6.QtWidgets import QPlainTextEdit, QWidget

# Matches an XML tag and captures the closing slash, the name and the self closing slash
TAG_PATTERN = re.compile(r"<(/?)([A-Za-z_][\w.:-]*)([^<>]*?)(/?)>")

# Highlighting patterns applied per line by the syntax highlighter
NAME_PATTERN = re.compile(r"</?([A-Za-z_][\w.:-]*)")
ATTRIBUTE_PATTERN = re.compile(r"([A-Za-z_][\w.:-]*)\s*=")
VALUE_PATTERN = re.compile(r"\"[^\"]*\"|'[^']*'")
COMMENT_PATTERN = re.compile(r"<!--.*?-->")
DECLARATION_PATTERN = re.compile(r"<\?.*?\?>")


class XmlHighlighter(QSyntaxHighlighter):
    def __init__(self, document, isDark=False):
        super().__init__(document)
        self.applyTheme(isDark)

    # Rebuild the character formats for the active theme
    def applyTheme(self, isDark):
        self.isDark = isDark

        tagColor = "#4ec9b0" if isDark else "#0b6a58"
        attributeColor = "#9cdcfe" if isDark else "#7a3e9d"
        valueColor = "#ce9178" if isDark else "#a31515"
        commentColor = "#6a9955" if isDark else "#4f8a3f"
        bracketColor = "#808080" if isDark else "#666666"

        self.tagFormat = self.buildFormat(tagColor, bold=True)
        self.attributeFormat = self.buildFormat(attributeColor)
        self.valueFormat = self.buildFormat(valueColor)
        self.commentFormat = self.buildFormat(commentColor, italic=True)
        self.bracketFormat = self.buildFormat(bracketColor)

        self.rehighlight()

    # Create a single character format from a colour and style flags
    def buildFormat(self, color, bold=False, italic=False):
        charFormat = QTextCharFormat()
        charFormat.setForeground(QColor(color))
        if bold:
            charFormat.setFontWeight(QFont.Weight.Bold)
        if italic:
            charFormat.setFontItalic(True)
        return charFormat

    # Apply the formats to a single block of text
    def highlightBlock(self, text):
        for match in re.finditer(r"[<>/]", text):
            self.setFormat(match.start(), 1, self.bracketFormat)

        for match in NAME_PATTERN.finditer(text):
            self.setFormat(match.start(1), match.end(1) - match.start(1), self.tagFormat)

        for match in ATTRIBUTE_PATTERN.finditer(text):
            self.setFormat(match.start(1), match.end(1) - match.start(1), self.attributeFormat)

        for match in VALUE_PATTERN.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.valueFormat)

        for match in DECLARATION_PATTERN.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.commentFormat)

        for match in COMMENT_PATTERN.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.commentFormat)


class FoldingMarginArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    # Width is driven by the editor so line numbers always fit
    def sizeHint(self):
        return QSize(self.editor.marginWidth(), 0)

    def paintEvent(self, event):
        self.editor.paintMargin(event)

    # Clicking a fold marker toggles the region that starts on that line
    def mousePressEvent(self, event):
        self.editor.handleMarginClick(event.position().toPoint())


class XmlCodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        editorFont = QFont("Consolas")
        editorFont.setStyleHint(QFont.StyleHint.Monospace)
        editorFont.setPointSize(9)
        self.setFont(editorFont)

        # Maps the first line of a foldable region to its last line
        self.foldRanges = {}
        self.foldedStarts = set()
        self.isDark = False

        self.marginArea = FoldingMarginArea(self)
        self.highlighter = XmlHighlighter(self.document(), self.isDark)

        self.blockCountChanged.connect(self.updateMarginWidth)
        self.updateRequest.connect(self.updateMarginArea)
        self.updateMarginWidth()

    # Repaint the editor and highlighter using the active theme colours
    def applyTheme(self, isDark, tokens=None):
        self.isDark = isDark
        self.highlighter.applyTheme(isDark)
        if tokens:
            self.marginBackground = QColor(tokens["alternateBase"])
            self.marginForeground = QColor(tokens["disabledText"])
            self.markerColor = QColor(tokens["text"])
        else:
            self.marginBackground = QColor("#333333" if isDark else "#e9e9ec")
            self.marginForeground = QColor("#7a7a7a" if isDark else "#9a9a9a")
            self.markerColor = QColor("#e6e6e6" if isDark else "#1c1c1c")
        self.marginArea.update()
        self.viewport().update()

    # Load XML text and recompute the foldable regions
    def setXmlText(self, text):
        self.foldedStarts.clear()
        self.setPlainText(text)
        self.foldRanges = self.computeFoldRanges(text)
        self.updateMarginWidth()
        self.marginArea.update()

    # Scan the document line by line and pair opening tags with their closing tags
    def computeFoldRanges(self, text):
        ranges = {}
        stack = []

        for lineIndex, line in enumerate(text.splitlines()):
            for match in TAG_PATTERN.finditer(line):
                isClosing = match.group(1) == "/"
                tagName = match.group(2)
                isSelfClosing = match.group(4) == "/"

                if isClosing:
                    # Unwind until the matching opening tag is found
                    while stack:
                        openTag, openLine = stack.pop()
                        if openTag == tagName:
                            if lineIndex > openLine:
                                ranges[openLine] = lineIndex
                            break
                elif not isSelfClosing:
                    stack.append((tagName, lineIndex))

        return ranges

    # Total width reserved for line numbers plus the fold marker column
    def marginWidth(self):
        digits = max(3, len(str(max(1, self.blockCount()))))
        digitWidth = QFontMetrics(self.font()).horizontalAdvance("9")
        return digitWidth * digits + 22

    def updateMarginWidth(self):
        self.setViewportMargins(self.marginWidth(), 0, 0, 0)

    def updateMarginArea(self, rect, dy):
        if dy:
            self.marginArea.scroll(0, dy)
        else:
            self.marginArea.update(0, rect.y(), self.marginArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateMarginWidth()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        contents = self.contentsRect()
        self.marginArea.setGeometry(QRect(contents.left(), contents.top(),
                                          self.marginWidth(), contents.height()))

    # Draw line numbers and the plus or minus fold markers
    def paintMargin(self, event):
        painter = QPainter(self.marginArea)
        painter.fillRect(event.rect(), self.marginBackground)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        markerSize = 9

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(self.marginForeground)
                painter.drawText(0, int(top), self.marginWidth() - 20,
                                 int(self.blockBoundingRect(block).height()),
                                 int(Qt.AlignmentFlag.AlignRight), str(blockNumber + 1))

                if blockNumber in self.foldRanges:
                    markerX = self.marginWidth() - 16
                    markerY = int(top) + (int(self.blockBoundingRect(block).height()) - markerSize) // 2
                    painter.setPen(self.markerColor)
                    painter.drawRect(markerX, markerY, markerSize, markerSize)
                    middleY = markerY + markerSize // 2
                    painter.drawLine(markerX + 2, middleY, markerX + markerSize - 2, middleY)
                    if blockNumber in self.foldedStarts:
                        middleX = markerX + markerSize // 2
                        painter.drawLine(middleX, markerY + 2, middleX, markerY + markerSize - 2)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    # Translate a click in the margin into a fold toggle
    def handleMarginClick(self, position):
        if position.x() < self.marginWidth() - 18:
            return

        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid():
            if block.isVisible() and top <= position.y() <= bottom:
                if block.blockNumber() in self.foldRanges:
                    self.toggleFold(block.blockNumber())
                return
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

    # Fold or unfold the region that starts on the given line
    def toggleFold(self, startLine):
        if startLine in self.foldedStarts:
            self.foldedStarts.discard(startLine)
        else:
            self.foldedStarts.add(startLine)
        self.refreshVisibility()

    # Collapse every foldable region in the document
    def foldAll(self):
        self.foldedStarts = set(self.foldRanges.keys())
        self.refreshVisibility()

    # Expand every foldable region in the document
    def unfoldAll(self):
        self.foldedStarts.clear()
        self.refreshVisibility()

    # Recompute block visibility from the set of collapsed regions
    def refreshVisibility(self):
        document = self.document()

        # Hidden lines are the union of all collapsed regions, children included
        hiddenLines = set()
        for startLine in self.foldedStarts:
            endLine = self.foldRanges.get(startLine)
            if endLine is None:
                continue
            hiddenLines.update(range(startLine + 1, endLine + 1))

        block = document.firstBlock()
        while block.isValid():
            shouldBeVisible = block.blockNumber() not in hiddenLines
            if block.isVisible() != shouldBeVisible:
                block.setVisible(shouldBeVisible)
            block = block.next()

        document.markContentsDirty(0, document.characterCount())
        self.viewport().update()
        self.marginArea.update()
        self.updateMarginWidth()

    # Scroll the view to the first line whose text contains the given needle
    def jumpToText(self, needle):
        cursor = self.document().find(needle)
        if not cursor.isNull():
            self.setTextCursor(cursor)
            self.centerCursor()
            return True
        return False

    # Reset the widget back to an empty document
    def clearContent(self):
        self.foldRanges = {}
        self.foldedStarts.clear()
        self.setPlainText("")
        self.marginArea.update()
