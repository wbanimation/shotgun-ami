from PySide import QtGui
import styles


def display(title, message, ok=True, cancel=True):
    msgBox = QtGui.QMessageBox()
    msgBox.setWindowTitle(title)
    msgBox.setStandardButtons(msgBox.Yes | msgBox.Cancel)
    msgBox.setDefaultButton(msgBox.Yes)
    msgBox.setText(message)
    msgBox.setPalette(QtGui.QPalette(styles.gui_bg_color))
    msgBox.setAutoFillBackground(True)
    msgBox.setFont(styles.normal_font)
    msgBox.setPalette(styles.messageBox_palette)
    msgBox.show()
    msgBox.raise_()
    return msgBox.exec_()
