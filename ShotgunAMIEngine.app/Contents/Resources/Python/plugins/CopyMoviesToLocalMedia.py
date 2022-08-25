#!/Applications/ShotgunAMIEngine.app/Contents/Frameworks/Python/bin/python

import sys
import os
import subprocess
import time
from PySide import QtGui, QtCore
from shotgun_api3 import Shotgun

app_name = "CopyMoviesToLocalMedia"
app_version = "0.1.73"

VALID_MOVIE_EXTENSIONS = ["mov", "mp4", "avi", "mxf"]
VALID_ENTITY_TYPES = ("Sequence", "Playlist", "Version", "PublishedFile")

# All of this stuff should really be in a config file
server_path = ""
script_name = ""
script_key = ""

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
normal_font.setPointSize(11)  # Font for all text
# small_font = QtGui.QFont()
# small_font.setPointSize(10)

# Folder paths
production_jobs_path = os.path.join(os.sep + "Volumes", "Production", "post", "jobs")
local_path = os.path.join(os.sep + "Volumes", "jobs")

# Look for Mounted Volumes
missing_volume = False
missing_volumes = []

if not os.path.isdir(production_jobs_path):
    found_production_path = False
    missing_volume = True
    missing_volumes.append("Production (speedy)")
else:
    found_production_path = True

if not os.path.isdir(local_path):
    found_local_path = False
    missing_volume = True
    missing_volumes.append("Local")
else:
    found_local_path = True


# ----------------------------------------------
# Entrypoint for this AMI
# ----------------------------------------------
def process_action(sg, logger, params):
    logger.info(params)
    main(sg, logger, params)


class progressGUI(QtGui.QWidget):
    def __init__(self, worker):
        QtGui.QWidget.__init__(self)
        self.worker = worker

        big_font = QtGui.QFont()
        big_font.setPointSize(11)  # Font for title
        big_font.setBold(True)

        normal_font = QtGui.QFont()
        normal_font.setPointSize(9)

        self.setPalette(QtGui.QPalette(gui_bg_color))
        self.setAutoFillBackground(True)

        self.setMinimumWidth(700)

        self.setWindowTitle("Copy Production Versions to Local Drive")

        self.task_label = QtGui.QLabel("Preparing to Copy Files..")
        self.task_label.setAlignment(QtCore.Qt.AlignLeft)
        self.task_label.setFont(big_font)
        self.task_label.setPalette(white_text)

        self.doing1_label = QtGui.QLabel(" ")
        self.doing1_label.setAlignment(QtCore.Qt.AlignLeft)
        self.doing1_label.setFont(normal_font)
        self.doing1_label.setPalette(white_text)
        self.doing2_label = QtGui.QLabel(" ")
        self.doing2_label.setAlignment(QtCore.Qt.AlignLeft)
        self.doing2_label.setFont(normal_font)
        self.doing2_label.setPalette(white_text)
        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.progress_bar.setValue(0)
        self.app_version_label = QtGui.QLabel("Version " + app_version)
        self.app_version_label.setAlignment(QtCore.Qt.AlignLeft)
        self.app_version_label.setFont(normal_font)
        self.app_version_label.setPalette(blue_text)
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
        self.worker.worker_done.connect(self.closeEvent)

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

    def messageBox(self, message_title, message):
        self.msgBox = QtGui.QMessageBox()
        self.msgBox.setWindowTitle(message_title)
        self.msgBox.setText(message)
        self.msgBox.setPalette(QtGui.QPalette(gui_bg_color))
        self.msgBox.setAutoFillBackground(True)
        self.msgBox.setFont(normal_font)
        self.msgBox.setModal(False)
        self.msgBox.show()
        self.msgBox.activateWindow()
        self.msgBox.raise_()

        return


class CopyProductionMediaLocalWorkThread(QtCore.QThread):

    update_progress_text = QtCore.Signal(str, str, str)
    update_progress_bar = QtCore.Signal(int)
    messageBoxSignal = QtCore.Signal(str, str)
    progress_bar_max = QtCore.Signal(int)
    worker_done = QtCore.Signal()

    def __init__(self, sg, params, logger, parent=None):
        super(CopyProductionMediaLocalWorkThread, self).__init__(parent)

        self.sg = sg
        self.params = params
        self.logger = logger
        # self.progress_window = progress_window

    # def update_progress_text(self, line1, line2="", line3=""):
    #     self.logger.info("%s %s %s" % (line1, line2, line3))
    #     self.progress_window.setDialogText(line1, line2, line3)

    def run(self):
        warning_message = False
        # progress_chunks = 0
        # all_entities = []

        sequence_tasks = [
            "Storyboard",
            "Layout",
            "Animation",
            "Compositing",
            "Overseas",
            "InternalAnimation",
            "AfterEffects",
            "Finishing",
        ]
        found_tasks = []

        # ensure we have a valid entity type. If not warn and return.
        if self.params["entity_type"] not in VALID_ENTITY_TYPES:
            self.update_progress_text.emit(
                "%s is not a valid entity type for this AMI. \n\nValid entity types are: %s"
                % (self.params["entity_type"], VALID_ENTITY_TYPES),
                "",
                "",
            )
            time.sleep(2)
            return False

        # set the progress window dialog
        self.update_progress_text.emit(
            "Getting Versions for %s IDs: %s"
            % (
                self.params["entity_type"],
                self.params["selected_ids"],
            ),
            "",
            "",
        )
        version_fields = [
            "id",
            "code",
            "project",
            "sg_path_to_movie",
            "sg_path_to_local_media",
            "sg_task",
        ]
        try:
            if self.params["entity_type"] == "Sequence":
                filters = [
                    ["sg_task.Task.content", "in", sequence_tasks],
                    [
                        "entity.Shot.sg_sequence.Sequence.id",
                        "in",
                        self.params["selected_ids"],
                    ],
                ]
                sg_versions = self.sg.find(
                    "Version",
                    filters,
                    version_fields,
                    additional_filter_presets={
                        "preset_name": "LATEST",
                        "latest_by": "ENTITIES_CREATED_AT",
                    },
                )
                for v in sg_versions:
                    if v["sg_task"] and v["sg_task"]["name"] not in found_tasks:
                        found_tasks.append(v["sg_task"]["name"])
            elif self.params["entity_type"] == "Playlist":
                self.logger.info("Finding Versions from Playlist")
                sg_versions = self.sg.find(
                    "Version",
                    [["playlists.Playlist.id", "in", self.params["selected_ids"]]],
                    version_fields,
                )
            elif self.params["entity_type"] == "Version":
                sg_versions = self.sg.find(
                    "Version",
                    [["id", "in", self.params["selected_ids"]]],
                    version_fields,
                )
            elif self.params["entity_type"] == "PublishedFile":
                sg_versions = self.sg.find(
                    "Version",
                    [
                        [
                            "published_files.PublishedFile.id",
                            "in",
                            self.params["selected_ids"],
                        ]
                    ],
                    version_fields,
                )
        except Exception as e:
            self.update_progress_text.emit("ERROR", str(e), "")
            time.sleep(5)

        self.update_progress_text.emit("Found %s Versions" % len(sg_versions), "", "")
        time.sleep(2)
        if not sg_versions:
            return False

        # Pre scan sg_versions to get progress total
        self.progress_bar_max.emit(len(sg_versions))
        # self.progress_window.setMaximum(len(sg_versions))
        self.logger.info("Set progress max to %s" % len(sg_versions))

        total_files = len(sg_versions)
        current_count = 0
        exists_count = 0
        copied_files = 0
        found_non_movie = False

        for v in sg_versions:
            current_count += 1
            path_to_movie = v["sg_path_to_movie"]
            path_to_local_media = v["sg_path_to_local_media"]
            # TODO: check to ensure path values exist.

            line1 = "Copying Files to Local Volume (%i of %i)" % (
                current_count,
                total_files,
            )
            line2 = "From: %s" % path_to_movie
            line3 = "To: %s" % path_to_local_media
            self.update_progress_text.emit(line1, line2, line3)
            self.update_progress_bar.emit(current_count)
            self.logger.info("set progress to %s" % current_count)
            # QtGui.qApp.processEvents()

            try:
                _, extension = path_to_movie.rsplit(".", 1)
            except Exception as e:
                message = (
                    "WARNING!\n\nUnable to get extention from Path to Movie: %s \n\n%s"
                    % (e, path_to_movie)
                )
                self.messageBoxSignal.emit("WARNING!", message)
                warning_message = True
                extension = None

            # Check to see if file exists on Local Media first
            # then make sure its a movie, we only want extensions from a set list
            if os.path.exists(path_to_local_media):
                exists_count += 1
                continue
            if extension not in VALID_MOVIE_EXTENSIONS:
                found_non_movie = True
                continue
            # make sure file were are copying exists
            if not os.path.exists(path_to_movie):
                message = (
                    "WARNING!\n\nPath to Movie does not exist!\n\n %s" % path_to_movie
                )
                self.messageBoxSignal.emit("WARNING!", message)
                warning_message = True
                continue

            # if the directory does not extist, create it
            path_to_local_media_dir = os.path.dirname(path_to_local_media)
            if not os.path.exists(path_to_local_media_dir):
                try:
                    os.makedirs(path_to_local_media_dir)
                except Exception as e:
                    message = (
                        "WARNING!\n\nCan't make Directory on Local Volume!\n\n%s" % e
                    )
                    self.messageBoxSignal.emit("WARNING!", message)
                    warning_message = True
                    continue

            # finally, copy the file with custom code
            try:
                self.customCopyfile(path_to_movie, path_to_local_media)
                copied_files += 1
            except Exception as e:
                message = "WARNING!\n\nCould not copy %s to %s\n\nError: %s" % (
                    path_to_movie,
                    path_to_local_media,
                    e,
                )
                self.messageBoxSignal.emit("WARNING!", message)
                warning_message = True
                continue

        found_tasks_str = ""
        if found_tasks:
            found_tasks_str = "Found Version Tasks: %s" % ", ".join(found_tasks)
        found_non_movie_str = ""
        if found_non_movie:
            found_non_movie_str = "Found non-movie media that was not copied."

        if not sg_versions and copied_files == 0:
            headline = "Found No Media to Copy."
        elif len(sg_versions) == exists_count:
            headline = "All Versions already exist locally."
        elif len(sg_versions) == copied_files:
            headline = "All Versions copied Successfully."
        elif found_non_movie:
            headline = ""
        else:
            headline = "Some Versions already exist locally and were not re-copied"

        self.update_progress_text.emit(headline, found_tasks_str, found_non_movie_str)
        time.sleep(2)

        if not warning_message:
            self.worker_done.emit()

        return False

    def customCopyfile(self, src, dst):

        try:
            O_BINARY = os.O_BINARY
        except Exception:
            O_BINARY = 0
        READ_FLAGS = os.O_RDONLY | O_BINARY
        WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | O_BINARY
        BUFFER_SIZE = 128 * 1024

        try:
            fin = os.open(src, READ_FLAGS)
            stat = os.fstat(fin)
            fout = os.open(dst, WRITE_FLAGS, stat.st_mode)
            for x in iter(lambda: os.read(fin, BUFFER_SIZE), ""):
                os.write(fout, x)
        finally:
            try:
                os.close(fin)
            except Exception:
                pass
            try:
                os.close(fout)
            except Exception:
                pass


def main(sg, logger, params):

    app = QtGui.QApplication(sys.argv)

    if missing_volume:
        message_title = "WARNING!"
        message = (
            "These required Volumes are not mounted...\n\n %s\n\nWould you like to try "
            "and mount the missing Volume(s)?" % "\n".join(missing_volumes)
        )

        msgBox = QtGui.QMessageBox()
        msgBox.setWindowTitle(message_title)
        msgBox.setStandardButtons(msgBox.Yes | msgBox.Cancel)
        msgBox.setDefaultButton(msgBox.Yes)
        msgBox.setText(message)
        msgBox.setPalette(QtGui.QPalette(gui_bg_color))
        msgBox.setAutoFillBackground(True)
        msgBox.setFont(normal_font)
        msgBox.setPalette(messageBox_palette)
        msgBox.show()
        msgBox.raise_()
        returnval = msgBox.exec_()

        if returnval == msgBox.Cancel:
            os._exit(0)
        else:
            for mount_volume in missing_volumes:
                if "Production" in mount_volume:
                    command = """osascript -e 'mount volume "smb://speedy.wba.aoltw.net/Production"'"""
                    p = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                if "Local" in mount_volume:
                    command = """osascript -e 'mount volume "jobs"'"""
                    p = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                p.communicate()  # now wait

    worker = CopyProductionMediaLocalWorkThread(sg, params, logger)
    dialog = progressGUI(worker)
    dialog.show()
    dialog.raise_()
    dialog.worker.start()

    sys.exit(app.exec_())
