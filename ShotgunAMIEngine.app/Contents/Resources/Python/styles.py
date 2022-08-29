from PySide import QtGui, QtCore


# GUI colors
gui_bg_color = QtGui.QColor(50, 50, 50)
# label_bg_color = QtGui.QColor(200, 200, 200)
white_text = QtGui.QPalette()
white_text.setColor(QtGui.QPalette.Foreground, QtCore.Qt.white)
# red_text = QtGui.QPalette()
# red_text.setColor(QtGui.QPalette.Foreground, QtCore.Qt.red)
# ltgray_text = QtGui.QPalette()
# ltgray_text.setColor(QtGui.QPalette.Foreground, QtCore.Qt.lightGray)
blue_text = QtGui.QPalette()
blue_text.setColor(QtGui.QPalette.Foreground, QtGui.QColor(60, 160, 250))

messageBox_palette = QtGui.QPalette()
messageBox_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.black)
messageBox_palette.setColor(QtGui.QPalette.Window, gui_bg_color)
messageBox_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)

big_font = QtGui.QFont()
big_font.setPointSize(18)  # Font for title
# med_font = QtGui.QFont()
# med_font.setPointSize(13)  # Font for message
normal_font = QtGui.QFont()
normal_font.setPointSize(12)  # Font for all text
# small_font = QtGui.QFont()
# small_font.setPointSize(10)
