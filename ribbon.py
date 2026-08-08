# Modern ribbon style tabbed command bar built from QToolButton groups
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QSizePolicy, QTabWidget,
                               QToolButton, QVBoxLayout, QWidget)

# Icon size used by the large buttons of a ribbon group
LARGE_ICON_SIZE = QSize(26, 26)

# Icon size used by the compact buttons of a ribbon group
COMPACT_ICON_SIZE = QSize(18, 18)

# Dynamic property marking the independently checkable data series buttons
SERIES_TOGGLE_PROPERTY = "seriesToggle"


class RibbonGroup(QWidget):
    def __init__(self, title, titleKey=None, parent=None):
        super().__init__(parent)

        self.titleKey = titleKey
        self.buttons = []

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(4, 2, 4, 2)
        outerLayout.setSpacing(2)

        self.buttonRow = QWidget()
        self.buttonLayout = QHBoxLayout(self.buttonRow)
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonLayout.setSpacing(2)
        self.buttonLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.titleLabel = QLabel(title)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.titleLabel.setStyleSheet("font-size: 10px; color: palette(mid);")

        outerLayout.addWidget(self.buttonRow, stretch=1)
        outerLayout.addWidget(self.titleLabel, stretch=0)

    # Add an existing QAction to the group as a large or compact tool button
    def addAction(self, action, isLarge=True, shortKey=None):
        button = QToolButton()
        button.setDefaultAction(action)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        if isLarge:
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIconSize(LARGE_ICON_SIZE)
            button.setMinimumWidth(70)
            button.setMaximumWidth(96)
        else:
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIconSize(COMPACT_ICON_SIZE)
            button.setMaximumWidth(148)

        # The marker lets the stylesheet tint only the data series toggles
        button.setProperty(SERIES_TOGGLE_PROPERTY,
                           bool(action.property(SERIES_TOGGLE_PROPERTY)))

        self.buttonLayout.addWidget(button)
        self.buttons.append((button, action, shortKey))
        self.applyButtonText(button, action, shortKey, None)
        return button

    # Add an arbitrary widget such as a combo box to the group
    def addWidget(self, widget):
        self.buttonLayout.addWidget(widget)
        return widget

    # Replace the caption shown under the button row
    def setTitle(self, title):
        self.titleLabel.setText(title)

    # Show the compact label on the button and keep the full text as a tooltip
    def applyButtonText(self, button, action, shortKey, lan):
        fullText = action.text()

        shortText = fullText
        if shortKey and lan is not None:
            shortText = lan.get(shortKey, fullText)
        elif shortKey:
            shortText = shortKey

        button.setText(shortText)

        # An action carrying its own tooltip wins over the plain full caption
        actionToolTip = action.toolTip()
        button.setToolTip(actionToolTip if actionToolTip and actionToolTip != fullText
                          else fullText)

    # Refresh every button caption and the group title after a language change
    def retranslate(self, lan):
        if self.titleKey:
            self.titleLabel.setText(lan.get(self.titleKey, self.titleLabel.text()))

        for button, action, shortKey in self.buttons:
            self.applyButtonText(button, action, shortKey, lan)


class RibbonPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.groups = []

        self.pageLayout = QHBoxLayout(self)
        self.pageLayout.setContentsMargins(4, 4, 4, 2)
        self.pageLayout.setSpacing(2)
        self.pageLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    # Create a titled group of commands and append a separator after it
    def addGroup(self, title, titleKey=None):
        group = RibbonGroup(title, titleKey)
        self.pageLayout.addWidget(group)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.pageLayout.addWidget(separator)

        self.groups.append(group)
        return group

    # Refresh every group of this page after a language change
    def retranslate(self, lan):
        for group in self.groups:
            group.retranslate(lan)


class RibbonBar(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.pages = {}
        self.pageTitleKeys = {}
        self.setDocumentMode(True)

        # Two line compact labels need a little more room than a single line
        self.setMaximumHeight(140)
        self.setMinimumHeight(140)

    # Register a new ribbon tab and return its page for populating
    def addPage(self, pageKey, title, titleKey=None):
        page = RibbonPage()
        self.addTab(page, title)
        self.pages[pageKey] = page
        self.pageTitleKeys[pageKey] = titleKey
        return page

    # Retrieve a previously created page by its key
    def page(self, pageKey):
        return self.pages.get(pageKey)

    # Update the tab captions after a language change
    def setPageTitle(self, pageKey, title):
        page = self.pages.get(pageKey)
        if page is None:
            return
        index = self.indexOf(page)
        if index >= 0:
            self.setTabText(index, title)

    # Refresh every tab, group caption and button caption after a language change
    def retranslate(self, lan):
        for pageKey, page in self.pages.items():
            titleKey = self.pageTitleKeys.get(pageKey)
            if titleKey:
                self.setPageTitle(pageKey, lan.get(titleKey, self.tabText(self.indexOf(page))))
            page.retranslate(lan)
