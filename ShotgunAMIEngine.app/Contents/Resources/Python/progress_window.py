from PySide import QtGui, QtCore
import os
import styles


class progressGUI(QtGui.QWidget):
    def __init__(self, worker, app_version):
        QtGui.QWidget.__init__(self)
        self.worker = worker

        big_font = QtGui.QFont()
        big_font.setPointSize(11)  # Font for title
        big_font.setBold(True)

        normal_font = QtGui.QFont()
        normal_font.setPointSize(9)

        self.setPalette(QtGui.QPalette(styles.gui_bg_color))
        self.setAutoFillBackground(True)

        self.setMinimumWidth(700)

        self.setWindowTitle("Copy Production Versions to Local Drive")

        self.task_label = QtGui.QLabel("Preparing to Copy Files..")
        self.task_label.setAlignment(QtCore.Qt.AlignLeft)
        self.task_label.setFont(big_font)
        self.task_label.setPalette(styles.white_text)

        self.doing1_label = QtGui.QLabel(" ")
        self.doing1_label.setAlignment(QtCore.Qt.AlignLeft)
        self.doing1_label.setFont(normal_font)
        self.doing1_label.setPalette(styles.white_text)
        self.doing2_label = QtGui.QLabel(" ")
        self.doing2_label.setAlignment(QtCore.Qt.AlignLeft)
        self.doing2_label.setFont(normal_font)
        self.doing2_label.setPalette(styles.white_text)
        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.progress_bar.setValue(0)
        self.app_version_label = QtGui.QLabel("Version %s" % app_version)
        self.app_version_label.setAlignment(QtCore.Qt.AlignLeft)
        self.app_version_label.setFont(normal_font)
        self.app_version_label.setPalette(styles.blue_text)
        self.cancel_button = QtGui.QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.closeEvent)

        button_box = QtGui.QHBoxLayout()
        button_box.addWidget(self.app_version_label)
        button_box.addStretch()
        button_box.addWidget(self.cancel_button)

        main_box = QtGui.QVBoxLayout()
        main_box.setContentsMargins(10, 10, 10, 10)
        main_box.setSpacing(6)
        main_box.addWidget(self.task_label)
        main_box.addWidget(self.doing1_label)
        main_box.addWidget(self.doing2_label)
        main_box.addWidget(self.progress_bar)
        main_box.addLayout(button_box)

        self.worker.update_progress_text.connect(self.setDialogText)
        self.worker.update_progress_bar.connect(self.set_progress)
        self.worker.messageBoxSignal.connect(self.messageBox)
        self.worker.progress_bar_max.connect(self.setMaximum)
        self.worker.worker_done.connect(self.update_cancel_button)

        self.setLayout(main_box)
        self.show

    def setMaximum(self, value):
        self.progress_bar.setMaximum(value)

    def setDialogText(self, doing, doing1="", doing2=""):
        self.task_label.setText(doing)
        self.doing1_label.setText(doing1)
        self.doing2_label.setText(doing2)

    def set_progress(self, value):
        self.progress_bar.setValue(value)

    def closeEvent(self):
        os._exit(0)

    def update_cancel_button(self):
        self.cancel_button.setText("OK")

    def messageBox(self, message_title, message):
        self.msgBox = QtGui.QMessageBox()
        self.msgBox.setWindowTitle(message_title)
        self.msgBox.setText(message)
        self.msgBox.setPalette(QtGui.QPalette(styles.gui_bg_color))
        self.msgBox.setAutoFillBackground(True)
        self.msgBox.setFont(styles.normal_font)
        self.msgBox.setModal(False)
        self.msgBox.show()
        self.msgBox.activateWindow()
        self.msgBox.raise_()
