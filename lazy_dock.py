# Dock widget that defers its rendering until it actually becomes visible
from PySide6.QtCore import QSize, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDockWidget, QMenu

import icons

# Size a floating dock is given when it is detached from the context menu
DETACHED_SIZE = QSize(900, 600)


class LazyDockWidget(QDockWidget):
    def __init__(self, title, objectName, refreshCallback=None, parent=None):
        super().__init__(title, parent)

        # A stable object name is required by QMainWindow.saveState and restoreState
        self.setObjectName(objectName)

        self.refreshCallback = refreshCallback
        self.isDirty = False
        self.isRefreshScheduled = False
        self.lan = {}

        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                         QDockWidget.DockWidgetFeature.DockWidgetClosable)

        self.visibilityChanged.connect(self.onVisibilityChanged)

    # Store the active translation dictionary for the title bar menu
    def setLanguage(self, lan):
        self.lan = lan or {}

    # Offer close and detach when the title bar strip is right clicked
    def contextMenuEvent(self, event):
        if not self.isTitleBarPosition(event.pos()):
            super().contextMenuEvent(event)
            return

        menu = QMenu(self)

        closeAction = QAction(icons.makeIcon("close"),
                              self.lan.get("dockClose", "Close window"), menu)
        closeAction.triggered.connect(self.close)
        menu.addAction(closeAction)

        detachAction = QAction(icons.makeIcon("detach"),
                               self.lan.get("dockDetach", "Detach to separate window"), menu)
        detachAction.setEnabled(not self.isFloating())
        detachAction.triggered.connect(self.detachToWindow)
        menu.addAction(detachAction)

        menu.exec(event.globalPos())
        event.accept()

    # True when a point sits in the title bar rather than the dock content
    def isTitleBarPosition(self, position):
        contentWidget = self.widget()
        if contentWidget is None:
            return True
        return position.y() < contentWidget.geometry().top()

    # Float the dock and give it a comfortable standalone size
    def detachToWindow(self):
        self.setFloating(True)
        self.resize(DETACHED_SIZE)
        self.show()
        self.raise_()

    # Mark the dock as stale and repaint soon when the user can actually see it
    def requestUpdate(self):
        if not self.isVisible():
            self.isDirty = True
            return

        # Coalesce bursts of requests from a single data load into one redraw
        self.isDirty = True
        if self.isRefreshScheduled:
            return
        self.isRefreshScheduled = True
        QTimer.singleShot(0, self.runScheduledRefresh)

    # Deferred entry point used by the coalescing timer
    def runScheduledRefresh(self):
        self.isRefreshScheduled = False
        if self.isDirty and self.isVisible():
            self.isDirty = False
            self.runRefresh()

    # Repaint a stale dock the moment it is shown or undocked into view
    def onVisibilityChanged(self, isVisible):
        if isVisible and self.isDirty:
            self.isDirty = False
            self.runRefresh()

    # Also cover the plain show path used when restoring a saved layout
    def showEvent(self, event):
        super().showEvent(event)
        if self.isDirty:
            self.isDirty = False
            self.runRefresh()

    # Invoke the registered redraw function if one was supplied
    def runRefresh(self):
        if callable(self.refreshCallback):
            self.refreshCallback()
