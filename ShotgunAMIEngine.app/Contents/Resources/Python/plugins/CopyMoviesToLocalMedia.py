#!/Applications/ShotgunAMIEngine.app/Contents/Frameworks/Python/bin/python

import sys
import os
import time
from PySide import QtGui, QtCore
import progress_window
import utils
import message_box

app_name = "CopyMoviesToLocalMedia"
app_version = "0.1.75"

VALID_MOVIE_EXTENSIONS = [".mov", ".mp4", ".avi", ".mxf"]
VALID_ENTITY_TYPES = ("Sequence", "Playlist", "Version", "PublishedFile")

# All of this stuff should really be in a config file
server_path = ""
script_name = ""
script_key = ""


# ----------------------------------------------
# Entrypoint for this AMI
# ----------------------------------------------
def process_action(sg, logger, params):
    logger.info(params)
    main(sg, logger, params)


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

        self._copied = []  # files copied successfully
        self._missing = []  # source files missing
        self._exists = []  # files already exist locally
        self._non_movie = []  # non-movie files
        self._warnings = []  # other misc warnings

    def run(self):

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

        for v in sg_versions:
            current_count += 1
            path_to_movie = v["sg_path_to_movie"]
            path_to_local_media = v["sg_path_to_local_media"]
            # TODO: check to ensure path values exist.

            line1 = "Copying <b>%s</b>... (%i of %i)" % (
                os.path.basename(path_to_movie),
                current_count,
                total_files,
            )
            line2 = "From: %s" % path_to_movie
            line3 = "To: %s" % path_to_local_media
            self.update_progress_text.emit(line1, line2, line3)
            self.update_progress_bar.emit(current_count)
            self.logger.info("set progress to %s" % current_count)
            # QtGui.qApp.processEvents()

            _, extension = os.path.splitext(path_to_movie)

            # Check to see if file exists on Local Media first
            # then make sure its a movie, we only want extensions from a set list
            if os.path.exists(path_to_local_media):
                self._exists.append(os.path.basename(path_to_local_media))
                continue
            if extension.lower() not in VALID_MOVIE_EXTENSIONS:
                self._non_movie.append(os.path.basename(path_to_local_media))
                continue
            # make sure file were are copying exists
            if not os.path.exists(path_to_movie):
                self._missing.append(path_to_movie)
                continue

            # if the directory does not extist, create it
            path_to_local_media_dir = os.path.dirname(path_to_local_media)
            if not os.path.exists(path_to_local_media_dir):
                try:
                    os.makedirs(path_to_local_media_dir)
                except Exception as e:
                    self._warnings.append(
                        "[%s] Unable to create local directory %s. (%s)"
                        % (
                            os.path.basename(path_to_local_media),
                            path_to_local_media_dir,
                            e,
                        )
                    )
                    continue

            # finally, copy the file with custom code
            try:
                self.customCopyfile(path_to_movie, path_to_local_media)
                self._copied.append(os.path.basename(path_to_movie))
            except Exception as e:
                self._warnings.append(
                    "Could not copy %s to %s. (%s)"
                    % (
                        path_to_movie,
                        path_to_local_media,
                        e,
                    )
                )
                continue

        details = ""
        if found_tasks:
            details += "Found Version Tasks: %s\n\n" % ", ".join(found_tasks)
        if self._non_movie:
            details += "The following non-movie media was skipped:\n- %s\n\n" % (
                "\n- ".join(self._non_movie)
            )
        if self._missing:
            details += "The following source movies were missing:\n- %s\n\n" % (
                "\n- ".join(self._missing)
            )
        if self._exists:
            details += "The following movies already exist locally:\n- %s\n\n" % (
                "\n- ".join(self._exists)
            )
        if self._warnings:
            details += "Additional warnings:\n- %s\n\n" % ("\n- ".join(self._warnings))

        if not sg_versions and not self._copied:
            headline = "Found no media to copy."
        elif len(sg_versions) == len(self._exists):
            headline = "All Versions already exist locally."
        elif len(sg_versions) == len(self._copied):
            headline = "All Versions copied successfully."
        else:
            headline = "Some warnings occurred."

        copied_str = "Copied %d of %d total files" % (len(self._copied), total_files)

        self.update_progress_text.emit(headline, details, copied_str)

        # if not warning_message:
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
    if not utils.check_volume_mounts(["production", "local"], logger):
        os._exit()

    worker = CopyProductionMediaLocalWorkThread(sg, params, logger)
    dialog = progress_window.progressGUI(worker, app_version)
    dialog.show()
    dialog.raise_()
    dialog.worker.start()

    sys.exit(app.exec_())
