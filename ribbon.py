# Modern ribbon style tabbed command bar built from QToolButton groups
from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
                               QTabWidget, QToolButton, QVBoxLayout, QWidget)

# Icon size used by the large buttons of a ribbon group
LARGE_ICON_SIZE = QSize(26, 26)

# Icon size used by the compact buttons of a ribbon group
COMPACT_ICON_SIZE = QSize(18, 18)

# Pixels scrolled per wheel notch or per overflow arrow click
RIBBON_SCROLL_STEP = 80

# Dynamic property marking the independently checkable data series buttons
SERIES_TOGGLE_PROPERTY = "seriesToggle"

# Dynamic property marking a button whose action discards results, tinted by the theme stylesheet
DESTRUCTIVE_BUTTON_PROPERTY = "destructiveAction"


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
            button.setMaximumWidth(112)
        else:
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIconSize(COMPACT_ICON_SIZE)
            button.setMaximumWidth(168)

        # Smaller text buys more characters per line so captions wrap instead of truncating
        button.setStyleSheet("QToolButton { font-size: 9px; }")

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


class RibbonPageContainer(QWidget):
    def __init__(self, page, parent=None):
        super().__init__(parent)

        self.page = page

        outerLayout = QHBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.setSpacing(0)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setWidget(page)
        self.scrollArea.viewport().installEventFilter(self)

        self.leftArrowButton = QToolButton()
        self.leftArrowButton.setArrowType(Qt.ArrowType.LeftArrow)
        self.leftArrowButton.setAutoRepeat(True)
        self.leftArrowButton.clicked.connect(self.scrollLeft)

        self.rightArrowButton = QToolButton()
        self.rightArrowButton.setArrowType(Qt.ArrowType.RightArrow)
        self.rightArrowButton.setAutoRepeat(True)
        self.rightArrowButton.clicked.connect(self.scrollRight)

        outerLayout.addWidget(self.leftArrowButton)
        outerLayout.addWidget(self.scrollArea, 1)
        outerLayout.addWidget(self.rightArrowButton)

        self.scrollArea.horizontalScrollBar().valueChanged.connect(self.updateArrowState)
        self.scrollArea.horizontalScrollBar().rangeChanged.connect(self.updateArrowState)
        self.updateArrowState()

    def scrollLeft(self):
        bar = self.scrollArea.horizontalScrollBar()
        bar.setValue(bar.value() - RIBBON_SCROLL_STEP)

    def scrollRight(self):
        bar = self.scrollArea.horizontalScrollBar()
        bar.setValue(bar.value() + RIBBON_SCROLL_STEP)

    # Hide both arrows once the page fits, disable whichever side is exhausted otherwise
    def updateArrowState(self, *_args):
        bar = self.scrollArea.horizontalScrollBar()
        hasOverflow = bar.maximum() > 0
        self.leftArrowButton.setVisible(hasOverflow)
        self.rightArrowButton.setVisible(hasOverflow)
        self.leftArrowButton.setEnabled(bar.value() > bar.minimum())
        self.rightArrowButton.setEnabled(bar.value() < bar.maximum())

    # Translate a Shift+Wheel or a horizontal tilt wheel into ribbon scrolling
    def eventFilter(self, watched, event):
        if watched is self.scrollArea.viewport() and event.type() == QEvent.Type.Wheel:
            tiltDelta = event.angleDelta().x()
            if tiltDelta:
                bar = self.scrollArea.horizontalScrollBar()
                bar.setValue(bar.value() - tiltDelta)
                return True
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                bar = self.scrollArea.horizontalScrollBar()
                bar.setValue(bar.value() - event.angleDelta().y())
                return True
        return super().eventFilter(watched, event)

    # Re-evaluate overflow whenever the window (and therefore the ribbon) is resized
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateArrowState()


class RibbonBar(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.pages = {}
        self.pageContainers = {}
        self.pageTitleKeys = {}
        self.setDocumentMode(True)

        # Two line compact labels need a little more room than a single line
        self.setMaximumHeight(140)
        self.setMinimumHeight(140)

    # Register a new ribbon tab and return its page for populating
    def addPage(self, pageKey, title, titleKey=None):
        page = RibbonPage()
        container = RibbonPageContainer(page)
        self.addTab(container, title)
        self.pages[pageKey] = page
        self.pageContainers[pageKey] = container
        self.pageTitleKeys[pageKey] = titleKey
        return page

    # Retrieve a previously created page by its key
    def page(self, pageKey):
        return self.pages.get(pageKey)

    # Update the tab captions after a language change
    def setPageTitle(self, pageKey, title):
        container = self.pageContainers.get(pageKey)
        if container is None:
            return
        index = self.indexOf(container)
        if index >= 0:
            self.setTabText(index, title)

    # Refresh every tab, group caption and button caption after a language change
    def retranslate(self, lan):
        for pageKey, page in self.pages.items():
            titleKey = self.pageTitleKeys.get(pageKey)
            if titleKey:
                container = self.pageContainers.get(pageKey)
                fallbackIndex = self.indexOf(container) if container is not None else -1
                self.setPageTitle(pageKey, lan.get(titleKey, self.tabText(fallbackIndex)))
            page.retranslate(lan)
