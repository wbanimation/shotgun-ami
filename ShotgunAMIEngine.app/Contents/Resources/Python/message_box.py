from PySide import QtGui
import styles


def display(title, message, ok_only=False):
    msgBox = QtGui.QMessageBox()
    msgBox.setWindowTitle(title)
    if not ok_only:
        msgBox.setStandardButtons(msgBox.Yes | msgBox.Cancel)
        msgBox.setDefaultButton(msgBox.Yes)
    else:
        msgBox.setStandardButtons(msgBox.Ok)
    msgBox.setText(message)
    msgBox.setPalette(QtGui.QPalette(styles.gui_bg_color))
    msgBox.setAutoFillBackground(True)
    msgBox.setFont(styles.normal_font)
    msgBox.setPalette(styles.messageBox_palette)
    msgBox.show()
    msgBox.raise_()
    return msgBox.exec_()
