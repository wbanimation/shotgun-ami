#!/Applications/ShotgunAMIEngine.app/Contents/Frameworks/Python/bin/python

app_name = "CopyMoviesToLocalMedia"
app_version = "0.1.73"

debug = True

import sys
import os
import shutil
import getpass
import socket
import urllib
import logging as logger
import threading
import subprocess
import re
import time
import webbrowser

import copy
from datetime import datetime
from PySide import QtGui, QtCore
from shotgun_api3 import Shotgun
from vendors import six

movie_extensions = ["mov", "mp4", "avi", "mxf"]

#    Project configuration
"""
All of this stuff should really be in a config file
"""
server_path = ""
script_name = ""
script_key = ""

# Log file
logfile = os.path.dirname(sys.argv[0]) + "/CopyMoviesToLocalMedia.log"


# GUI colors
gui_bg_color = QtGui.QColor(50, 50, 50)
label_bg_color = QtGui.QColor(200, 200, 200)
white_text = QtGui.QPalette()
white_text.setColor(QtGui.QPalette.Foreground, QtCore.Qt.white)
red_text = QtGui.QPalette()
red_text.setColor(QtGui.QPalette.Foreground, QtCore.Qt.red)
ltgray_text = QtGui.QPalette()
ltgray_text.setColor(QtGui.QPalette.Foreground, QtCore.Qt.lightGray)
blue_text = QtGui.QPalette()
blue_text.setColor(QtGui.QPalette.Foreground, QtGui.QColor(60, 160, 250))

messageBox_palette = QtGui.QPalette()
messageBox_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.black)
messageBox_palette.setColor(QtGui.QPalette.Window, gui_bg_color)
messageBox_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)

big_font = QtGui.QFont()
big_font.setPointSize(18)  # Font for title
med_font = QtGui.QFont()
med_font.setPointSize(13)  # Font for message
normal_font = QtGui.QFont()
normal_font.setPointSize(11)  # Font for all text
small_font = QtGui.QFont()
small_font.setPointSize(10)

# Folder paths
production_path = os.path.join(os.sep + "Volumes", "Production", "post", "jobs")
local_path = os.path.join(os.sep + "Volumes", "jobs")

# Look for Mounted Volumes
missing_volume = False
missing_volumes = []

if debug:
    print("\nChecking for mounted Volumes...\n")

if not os.path.isdir(production_path):
    found_production_path = False
    missing_volume = True
    missing_volumes.append("Production (speedy)")
    if debug:
        print(
            " WARNING! No Production Volume Detected, Disabling Production Copy Option..."
        )
else:
    if debug:
        print(" Production Volume Detected...")
    found_production_path = True

if not os.path.isdir(local_path):
    found_local_path = False
    missing_volume = True
    missing_volumes.append("Local")
    if debug:
        print(" WARNING! No Local Volume Detected, Disabling Local Copy Option...\n")
else:
    if debug:
        print(" Local Volume Detected...")
    found_local_path = True

if debug:
    if not missing_volume:
        print("\n   ALL VOLUMES ARE MOUNTED!")
    if debug:
        print("-" * 80)

# Get Shotgun connection
sg = Shotgun(server_path, script_name, script_key)


# ----------------------------------------------
# Required logging sub
# ----------------------------------------------
def process_action(sg, logger, params):
    logger.info(params)


# ----------------------------------------------
# Generic Shotgun Exception Class
# ----------------------------------------------
class ShotgunException(Exception):
    pass


# ----------------------------------------------
# Set up logging
# ----------------------------------------------
def init_log(filename="version_packager.log"):
    try:
        logger.basicConfig(
            level=logger.DEBUG,
            format="%(asctime)s %(levelname)-8s %(message)s",
            datefmt="%Y-%b-%d %H:%M:%s",
            filename=filename,
            filemode="w+",
        )
    except IOError as e:
        raise ShotgunException("Unable to open logfile for writing: %s" % e)
    logger.info("Export Notes logging started.")
    return logger


# ----------------------------------------------
# ShotgunAction Class to manage ActionMenuItem call
# ----------------------------------------------
class ShotgunAction:
    def __init__(self, url):
        self.logger = self._init_log(logfile)
        self.url = url
        self.protocol, self.action, self.params = self._parse_url()

        # entity type that the page was displaying
        self.entity_type = self.params["entity_type"]

        # Project info (if the ActionMenuItem was launched from a page not belonging
        # to a Project (Global Page, My Page, etc.), this will be blank
        if "project_id" in self.params:
            self.project = {
                "id": int(self.params["project_id"]),
                "name": self.params["project_name"],
            }
        else:
            self.project = None

        # Internal column names currently displayed on the page
        self.columns = self.params["cols"]

        # Human readable names of the columns currently displayed on the page
        self.column_display_names = self.params["column_display_names"]

        # All ids of the entities returned by the query (not just those visible on the page)
        self.ids = []
        if len(self.params["ids"]) > 0:
            ids = self.params["ids"].split(",")
            self.ids = [int(id) for id in ids]

        # All ids of the entities returned by the query in filter format ready
        # to use in a find() query
        self.ids_filter = self._convert_ids_to_filter(self.ids)

        # ids of entities that were currently selected
        self.selected_ids = []
        if len(self.params["selected_ids"]) > 0:
            sids = self.params["selected_ids"].split(",")
            self.selected_ids = [int(id) for id in sids]

        # All selected ids of the entities returned by the query in filter format ready
        # to use in a find() query
        self.selected_ids_filter = self._convert_ids_to_filter(self.selected_ids)

        # sort values for the page
        # (we don't allow no sort anymore, but not sure if there's legacy here)
        if "sort_column" in self.params:
            self.sort = {
                "column": self.params["sort_column"],
                "direction": self.params["sort_direction"],
            }
        else:
            self.sort = None

        # title of the page
        self.title = self.params["title"]

        # user info who launched the ActionMenuItem
        self.user = {"id": self.params["user_id"], "login": self.params["user_login"]}

        # session_uuid
        self.session_uuid = self.params["session_uuid"]

    # ----------------------------------------------
    # Set up logging
    # ----------------------------------------------
    def _init_log(self, filename="shotgun_action.log"):
        try:
            logger.basicConfig(
                level=logger.DEBUG,
                format="%(asctime)s %(levelname)-8s %(message)s",
                datefmt="%Y-%b-%d %H:%M:%S",
                filename=filename,
                filemode="w+",
            )
        except IOError as e:
            raise ShotgunActionException("Unable to open logfile for writing: %s" % e)
        logger.info("ShotgunAction logging started.")
        return logger

    # ----------------------------------------------
    # Parse ActionMenuItem call into protocol, action and params
    # ----------------------------------------------
    def _parse_url(self):
        logger.info("Parsing full url received: %s" % self.url)

        # get the protocol used
        protocol, path = self.url.split(":", 1)
        logger.info("protocol: %s" % protocol)

        # extract the action
        action, params = path.split("?", 1)
        action = action.strip("/")
        logger.info("action: %s" % action)

        # extract the parameters
        # 'column_display_names' and 'cols' occurs once for each column displayed so we store it as a list
        params = params.split("&")
        p = {"column_display_names": [], "cols": []}
        for arg in params:
            try:
                key, value = map(urllib.unquote, arg.split("=", 1))
                if key == "column_display_names" or key == "cols":
                    p[key].append(value)
                else:
                    p[key] = value
            except Exception as e:
                if debug:
                    print(" WARNING!: Upack/Split failed...: %s" % e)

        params = p
        logger.info("params: %s" % params)
        return (protocol, action, params)

    # ----------------------------------------------
    # Convert IDs to filter format to us in find() queries
    # ----------------------------------------------
    def _convert_ids_to_filter(self, ids):
        filter = []
        for id in ids:
            filter.append(["id", "is", id])
        logger.debug("parsed ids into: %s" % filter)
        return filter


# ----------------------------------------------
# Extract Attachment id from entity field
# ----------------------------------------------
def extract_attachment_id(attachment):
    # extract the Attachment id from the url location
    #    attachment_id = attachment['url'].rsplit('/',1)[1]
    attachment_id = attachment["id"]

    try:
        attachment_id = int(attachment_id)
    except ValueError:
        # not an integer.
        return None

    return attachment_id


"""
-------------------------------------------------------------------------------
All of the above stuff is needed to process the input from the AMI
"""


class progressGUI(QtGui.QWidget):

    messageBoxSignal = QtCore.Signal(str, str)

    def __init__(self):
        QtGui.QWidget.__init__(self)

        self.messageBoxSignal.connect(self.messageBox)

        big_font = QtGui.QFont()  #
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

        self.setLayout(main_box)
        self.show

    def setMaximum(self, value):
        self.progress_bar.setMaximum(value)

    def setDialogText(self, doing, doing1="", doing2=""):
        self.task_label.setText(doing)
        self.doing1_label.setText(doing1)
        self.doing2_label.setText(doing2)

    def setProgress(self, value):
        self.progress_bar.setValue(value)

    def closeEvent(self):
        if debug:
            print("-" * 80)
            print("\n QUITING\n")
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


class CopyProductionMediaLocalWorkThread(threading.Thread):
    def __init__(self, sg, sa, progress_window):
        threading.Thread.__init__(self)

        self.sg = sg
        self.sa = sa
        self.progress_window = progress_window

    def run(self):
        global selected_version_ids

        warning_message = False
        progress_chunks = 0
        all_entities = []

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

        if self.sa.params["entity_type"] in ("Playlist", "Version", "Sequence"):

            if self.sa.params["entity_type"] == "Sequence":
                selected_ids = self.sa.params["selected_ids"]

                if debug:
                    print(" selected_ids: ", selected_ids)

                if len(selected_ids) > 0:
                    selected_ids = [selected_ids]

                selected_filter = []
                for sequence_id in selected_ids:
                    version_filter = ["id", "is", int(sequence_id)]
                    selected_filter.append(version_filter)

                sg_sequences = self.sg.find(
                    "Sequence", selected_filter, ["code"], filter_operator="any"
                )

                additional_filter_presets = [
                    {"preset_name": "LATEST", "latest_by": "ENTITIES_CREATED_AT"}
                ]

                doing = "Sequence " + sg_sequences[0]["code"]
                doing1 = " Getting Versions For Tasks: " + ", ".join(sequence_tasks)
                doing2 = " "
                self.progress_window.setDialogText(doing, doing1, doing2)

                entities = []
                for task in sequence_tasks:
                    filters = [
                        ["sg_task.Task.content", "is", task],
                        [
                            "entity.Shot.sg_sequence",
                            "is",
                            {"type": "Sequence", "id": int(selected_ids[0])},
                        ],
                    ]

                    task_entities = self.sg.find(
                        "Version",
                        filters,
                        [
                            "code",
                            "project",
                            "id",
                            "sg_production_path",
                            "sg_path_to_movie",
                        ],
                        additional_filter_presets=additional_filter_presets,
                    )

                    if len(task_entities) > 0:
                        entities = entities + task_entities
                        found_tasks.append(task)

            else:
                self.progress_window.setDialogText(
                    "Doing else. Version Ids: %s" % selected_version_ids
                )
                time.sleep(2)
                selected_filter = []
                selected_version_ids_list = []

                if "," in selected_version_ids:
                    selected_version_ids = selected_version_ids.split(",")

                for version_id in selected_version_ids:
                    version_filter = ["id", "is", int(version_id)]
                    selected_filter.append(version_filter)

                entities = self.sg.find(
                    "Version",
                    selected_filter,
                    ["project", "id", "sg_production_path", "sg_path_to_movie"],
                    filter_operator="any",
                )
                self.progress_window.setDialogText("Found %s Versions" % len(entities))
                time.sleep(2)

        elif self.sa.params["entity_type"] == "PublishedFile":
            entities = self.sg.find(
                "PublishedFile",
                self.sa.selected_ids_filter,
                ["project", "id", "path"],
                filter_operator="any",
            )

        if debug:
            print(" entities:", entities)

        if len(entities) == 0:
            doing = "Found no Versions..."
            doing1 = "  "
            doing2 = "  "
            self.progress_window.setDialogText(doing, doing1, doing2)
            time.sleep(2)
            return False

        else:

            # Pre scan entities to get progress total
            total_progress = 0

            for e in entities:
                total_progress += 1

            self.progress_window.setMaximum(total_progress)

            progress = 0

            if debug:
                print("Copying Files to Local Media...")
                print("-" * 80)

            copy_count = len(entities)
            doing_count = 1
            exists_count = 0
            copied_files = 0
            found_non_movie = False

            doing = "Copying Files to Local Volume (%i of %i)" % (
                doing_count,
                copy_count,
            )

            for e in entities:

                if e["type"] == "Version":
                    project, id, production_path, path_to_movie = (
                        e["project"]["name"],
                        e["id"],
                        str(e["sg_production_path"]),
                        str(e["sg_path_to_movie"]),
                    )

                elif e["type"] == "PublishedFile":
                    project, id, production_path = (
                        e["project"]["name"],
                        e["id"],
                        str(e["path"]["local_path"]),
                    )
                    split_production_path = production_path.split("/", 4)
                    path_to_movie = os.path.join(
                        os.sep, split_production_path[1], split_production_path[4]
                    )

                if debug:
                    print("production_path:", production_path)
                    print("  path_to_movie:", path_to_movie)

                progress += 1

                try:
                    minus_extension, extension = production_path.rsplit(".", 1)
                except Exception as e:
                    message = (
                        "WARNING!\n\nUnable to get extention from Production path: %s \n\n%s"
                        % (e, production_path)
                    )
                    self.progress_window.messageBoxSignal.emit("WARNING!", message)
                    warning_message = True
                    extension = None

                # Check to see if file exists on Local Media first
                # then make sure its a movie, we only want extensions from a set list
                if not os.path.exists(path_to_movie) and extension in movie_extensions:
                    doing = "Copying Files to Local Volume (%i of %i)" % (
                        doing_count,
                        copy_count,
                    )
                    doing1 = "       From: %s" % production_path
                    doing2 = "         To: %s\n" % path_to_movie
                    self.progress_window.setDialogText(doing, doing1, doing2)
                    self.progress_window.setProgress(progress)
                    QtGui.qApp.processEvents()
                    path_to_movie_dir = path_to_movie.rsplit("/", 1)[0]

                    # make sure file were are copying exists
                    if not os.path.exists(production_path):
                        message = (
                            "WARNING!\n\nProduction path does not exists!\n\n "
                            + production_path
                        )
                        self.progress_window.messageBoxSignal.emit("WARNING!", message)
                        warning_message = True
                        if debug:
                            print("   'production_path' not found: Skipping...")
                        doing_count += 1

                    # if the directory does not extist, create it
                    elif not os.path.exists(path_to_movie_dir):
                        try:
                            os.makedirs(path_to_movie_dir)
                        except Exception as e:
                            message = (
                                "WARNING!\n\nCan't make Directory on Local Volume!\n\n%s"
                                % e
                            )
                            self.progress_window.messageBoxSignal.emit(
                                "WARNING!", message
                            )
                            warning_message = True
                    # finally, copy the file with custom code
                    try:
                        self.customCopyfile(production_path, path_to_movie)
                        doing_count += 1
                        copied_files += 1

                    except Exception as e:
                        message = (
                            "WARNING!\n\nCould not copy "
                            + production_path
                            + " to "
                            + path_to_movie
                            + "\n\n%s" % e
                        )
                        self.progress_window.messageBoxSignal.emit("WARNING!", message)
                        warning_message = True
                        doing_count += 1

                else:
                    if debug:
                        print("   file exisits: Skipping...")
                    doing_count += 1
                    if extension in movie_extensions:
                        exists_count += 1
                    else:
                        found_non_movie = True

            if debug:
                print("entities:", len(entities))
                print("copied_files:", copied_files)
                print("exists_count:", exists_count)
                print("found_non_movie:", found_non_movie)

            if len(entities) < 0 and copied_files == 0:
                doing = "FoundNo Media to Copy..."
                if len(found_tasks) > 0:
                    doing1 = "  Found Version Tasks : " + ", ".join(found_tasks)
                else:
                    doing1 = " "
                if found_non_movie:
                    doing2 = "  Found Non-Movie Media. These Were Skipped..."
                else:
                    doing2 = "  "
                self.progress_window.setDialogText(doing, doing1, doing2)
                time.sleep(2)

            elif len(entities) == exists_count:
                doing = "All Version Alredy Exist on Local Media..."
                if len(found_tasks) > 0:
                    doing1 = "  Found Version Tasks : " + ", ".join(found_tasks)
                else:
                    doing1 = " "
                if found_non_movie:
                    doing2 = "  Found Non-Movie Media. These Were Skipped..."
                else:
                    doing2 = "  "
                self.progress_window.setDialogText(doing, doing1, doing2)
                time.sleep(2)

            elif len(entities) == copied_files:

                doing = "All Version Copied Successfully..."
                if len(found_tasks) > 0:
                    doing1 = "  Found Version Tasks : " + ", ".join(found_tasks)
                else:
                    doing1 = " "
                if found_non_movie:
                    doing2 = "  Found Non-Movie Media. These Were Skipped..."
                else:
                    doing2 = "  "
                self.progress_window.setDialogText(doing, doing1, doing2)
                time.sleep(2)

            elif found_non_movie:

                doing = "Found Non-Movie Media. These Were Skipped..."
                if len(found_tasks) > 0:
                    doing1 = "  Found Version Tasks : " + ", ".join(found_tasks)
                else:
                    doing1 = " "
                doing2 = "  "
                self.progress_window.setDialogText(doing, doing1, doing2)
                time.sleep(2)

            else:

                doing = "Some Versions Alredy Existsed and Were Skipped..."
                if len(found_tasks) > 0:
                    doing1 = "  Found Version Tasks : " + ", ".join(found_tasks)
                else:
                    doing1 = " "
                doing2 = "  "
                self.progress_window.setDialogText(doing, doing1, doing2)
                time.sleep(2)

            if not warning_message:
                self.progress_window.closeEvent()

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


def main():
    if debug:
        print("\n STARTING CopyProductionVersionLocal", app_version)
        print("-" * 80)

    global selected_version_ids

    init_log(logfile)

    try:
        sa = ShotgunAction(sys.argv[1])
    # 	logger.info("Firing... %s" % (sys.argv[1]) )
    except IndexError as e:
        raise ShotgunException("Missing POST arguments")

    # Check that the correct action is happening
    if sa.action == "CopyMoviesToLocalMedia":
        app = QtGui.QApplication(sys.argv)
        selected_version_ids = []

        if missing_volume:
            message_title = "WARNING!"
            message = (
                "These required Volumes are not mounted...\n\n"
                + "\n".join(missing_volumes)
                + "\n\nWould you like me to try and mount the missing Volume(s)?"
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
                    if debug:
                        print("\n MOUNTING VOLUME: " + mount_volume)
                    p.communicate()  # now wait

        if "entity_type" in sa.params:
            if sa.params["entity_type"] == "Playlist":
                if debug:
                    print(" GOT Playlist....")
                if "selected_ids" in sa.params:
                    selected_ids = sa.params["selected_ids"]
                    try:
                        selected_ids = selected_ids.split(",")
                    except Exception:
                        pass

                    for playlist_id in selected_ids:
                        sg_playlist = sg.find_one(
                            "Playlist",
                            [["id", "is", int(playlist_id)]],
                            ["code", "sg_type", "sg_episode", "created_at"],
                        )

                        if sg_playlist == None:
                            if debug:
                                print("WARNING! Playlist disappeared...")
                            continue
                        if "sg_type" in sg_playlist.keys():
                            playlist_type = sg_playlist["sg_type"]
                        else:
                            playlist_type = ""
                        playlist_name = sg_playlist["code"]
                        sg_playlist_versions = sg.find(
                            "Version",
                            [["playlists", "is", sg_playlist]],
                            ["id", "code", "entity", "sg_episode", "sg_status_list"],
                        )

                        for sg_version in sg_playlist_versions:
                            selected_version_ids.append(sg_version["id"])

            if sa.params["entity_type"] == "Version":
                if debug:
                    print(" GOT Versions....")
                selected_ids = sa.params["selected_ids"]

                if "," in selected_ids:
                    selected_version_ids = selected_ids.split(",")
                elif isinstance(selected_ids, str):
                    selected_version_ids.append(selected_ids)

        dialog = progressGUI()
        dialog.show()
        dialog.raise_()

        CopyProductionMediaLocalWorkThread(sg, sa, dialog).start()
        sys.exit(app.exec_())

    else:
        raise ShotgunException("Unknown action... :%s" % sa.action)


main()
