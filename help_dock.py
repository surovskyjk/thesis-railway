# Help panel rendering the project README as formatted markdown inside the GUI
import io
import os
import sys

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QTextDocument
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)

import icons

# Name of the documentation file rendered by this panel
README_NAME = "README.md"


class HelpWidget(QWidget):
    def __init__(self, lan, parent=None):
        super().__init__(parent)

        self.lan = lan

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        searchRow = QWidget()
        searchLayout = QHBoxLayout(searchRow)
        searchLayout.setContentsMargins(4, 4, 4, 4)
        searchLayout.setSpacing(4)

        self.searchField = QLineEdit()
        self.searchField.setPlaceholderText(lan.get("helpSearch", "Search the documentation"))
        self.searchField.returnPressed.connect(self.findNext)
        searchLayout.addWidget(self.searchField)

        self.searchButton = QToolButton()
        self.searchButton.setIcon(icons.makeIcon("search"))
        self.searchButton.setToolTip(lan.get("helpSearch", "Search the documentation"))
        self.searchButton.clicked.connect(self.findNext)
        searchLayout.addWidget(self.searchButton)

        self.reloadButton = QToolButton()
        self.reloadButton.setIcon(icons.makeIcon("resetView"))
        self.reloadButton.setToolTip(lan.get("helpReload", "Reload"))
        self.reloadButton.clicked.connect(self.reloadDocument)
        searchLayout.addWidget(self.reloadButton)

        layout.addWidget(searchRow)

        self.textBrowser = QTextBrowser()
        self.textBrowser.setOpenLinks(False)
        self.textBrowser.setOpenExternalLinks(False)
        self.textBrowser.anchorClicked.connect(self.openAnchor)
        layout.addWidget(self.textBrowser)

        self.reloadDocument()

    # Read the README from disk and render it as GitHub flavoured markdown
    def reloadDocument(self):
        markdown = self.readReadme()
        if markdown is None:
            self.textBrowser.setPlainText(
                self.lan.get("helpMissing", "README.md was not found next to the application."))
            return

        self.textBrowser.document().setMarkdown(
            markdown, QTextDocument.MarkdownFeature.MarkdownDialectGitHub)

    # Locate and read the README both when running from source and when frozen
    def readReadme(self):
        for candidate in self.readmeCandidates():
            if os.path.isfile(candidate):
                try:
                    return io.open(candidate, encoding="utf-8").read()
                except OSError:
                    continue
        return None

    # Directories the README may live in depending on how the app was started
    def readmeCandidates(self):
        searchRoots = [os.path.dirname(os.path.abspath(__file__))]

        # PyInstaller unpacks bundled data files into a temporary directory
        bundleRoot = getattr(sys, "_MEIPASS", None)
        if bundleRoot:
            searchRoots.insert(0, bundleRoot)
        searchRoots.append(os.path.dirname(os.path.abspath(sys.argv[0])))

        return [os.path.join(root, README_NAME) for root in searchRoots]

    # Highlight the next occurrence of the search term, wrapping at the end
    def findNext(self):
        term = self.searchField.text().strip()
        if not term:
            return

        if not self.textBrowser.find(term):
            self.textBrowser.moveCursor(self.textBrowser.textCursor().MoveOperation.Start)
            self.textBrowser.find(term)

    # Send external links to the system browser instead of loading them inline
    def openAnchor(self, url):
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
            return
        self.textBrowser.scrollToAnchor(url.fragment())

    # Refresh the control captions after a language change
    def updateTexts(self, lan):
        self.lan = lan
        self.searchField.setPlaceholderText(lan.get("helpSearch", "Search the documentation"))
        self.searchButton.setToolTip(lan.get("helpSearch", "Search the documentation"))
        self.reloadButton.setToolTip(lan.get("helpReload", "Reload"))

    # Repaint the icons when the theme changes
    def applyTheme(self, isDark, tokens=None):
        self.searchButton.setIcon(icons.makeIcon("search"))
        self.reloadButton.setIcon(icons.makeIcon("resetView"))
