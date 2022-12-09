from PySide import QtGui, QtCore
import os
import styles
import message_box


class progressGUI(QtGui.QWidget):
    def __init__(self, worker, window_title, app_version):
        QtGui.QWidget.__init__(self)
        self.window_title = window_title
        self.app_version = app_version

        self.worker = worker
        self.setupUi()
        self.worker.start()

    def setupUi(self):
        self.setPalette(QtGui.QPalette(styles.gui_bg_color))
        self.setAutoFillBackground(True)
        self.setMinimumWidth(700)
        self.setWindowTitle(self.window_title)

        self.task_label = QtGui.QLabel("Preparing to Copy Files..")
        self.task_label.setAlignment(QtCore.Qt.AlignLeft)
        self.task_label.setFont(styles.big_font)
        self.task_label.setPalette(styles.white_text)

        self.doing1_label = QtGui.QLabel(" ")
        self.doing1_label.setAlignment(QtCore.Qt.AlignLeft)
        self.doing1_label.setFont(styles.normal_font)
        self.doing1_label.setPalette(styles.white_text)
        self.doing2_label = QtGui.QLabel(" ")
        self.doing2_label.setAlignment(QtCore.Qt.AlignLeft)
        self.doing2_label.setFont(styles.normal_font)
        self.doing2_label.setPalette(styles.white_text)
        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.progress_bar.setValue(0)
        self.app_version_label = QtGui.QLabel("Version %s" % self.app_version)
        self.app_version_label.setAlignment(QtCore.Qt.AlignLeft)
        self.app_version_label.setFont(styles.normal_font)
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

        self.worker.signals.update_copy_progress.connect(self.setCopyProgress)
        self.worker.signals.update_progress_text.connect(self.setDialogText)
        self.worker.signals.update_progress_bar.connect(self.set_progress)
        self.worker.signals.progress_bar_max.connect(self.setMaximum)
        self.worker.signals.worker_done.connect(self.worker_done)
        self.worker.signals.show_message_box.connect(self.show_message_box)
        self.worker.signals.abort_mission.connect(self.abort_mission)

        self.setLayout(main_box)
        self.show()

    def setMaximum(self, value):
        self.progress_bar.setMaximum(value)

    def setDialogText(self, header, message=""):
        self.task_label.setText(header)
        self.doing1_label.setText(message)

    def setCopyProgress(self, msg):
        """
        Display the copy progress for each individual file

        Args:
            msg (str): message to display
        """
        self.doing2_label.setText(msg)

    def set_progress(self, value):
        self.progress_bar.setValue(value)

    def closeEvent(self):
        os._exit(0)

    def abort_mission(self, msg=""):
        if msg:
            self.show_message_box("Error", msg, True)
        self.closeEvent()

    def worker_done(self):
        self.cancel_button.setText("OK")
        self.raise_()

    def show_message_box(self, title, message, ok_only=False):
        ret_val = message_box.display(title, message, ok_only)
        if ret_val == QtGui.QMessageBox.Cancel:
            self.worker._continue = False
