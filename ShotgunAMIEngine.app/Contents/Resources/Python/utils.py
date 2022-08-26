import os
import subprocess
import message_box
from PySide import QtGui, QtCore

FILESERVERS = {
    "droid": {"path": "/Volumes/DROID", "mount": "smb://droid.wba.aoltw.net"},
    "droid2": {"path": "/Volumes/DROID2", "mount": "smb://droid2.wba.aoltw.net"},
    "droid3": {"path": "/Volumes/DROID3", "mount": "smb://droid3.wba.aoltw.net"},
    "production": {
        "path": "/Volumes/Production",
        "mount": "smb://speedy.wba.aoltw.net/Production",
    },
    "local": {"path": "/Volumes/jobs", "mount": "jobs"},
}


def validate_volume_name(volume_name):
    if volume_name not in FILESERVERS.keys():
        raise ValueError(
            "Invalid Volume name %s. Valid Volumes are: %s"
            % (
                volume_name,
                list(FILESERVERS.keys()),
            )
        )


def is_mounted(volume_name):
    volume_name = volume_name.lower()
    validate_volume_name(volume_name)
    return os.path.isdir(FILESERVERS[volume_name]["path"])


def mount_volume(volume_name):
    volume_name = volume_name.lower()
    validate_volume_name(volume_name)
    volume = FILESERVERS[volume_name]

    command = "osascript -e 'mount volume \"%s\"'" % volume["mount"]
    p = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    p.communicate()  # now wait


def check_volume_mounts(volumes, logger):
    """
    Checks all volumes are mounted. If user cancels or volumes don't get mounted
    correctly, we return False to indicate exit. Otherwise True and continue

    :param volumes _type_: _description_
    :param logger _type_: _description_
    :returns _type_: _description_
    """
    missing_volumes = []
    for volume in volumes:
        if not is_mounted(volume):
            missing_volumes.append(volume)

    if missing_volumes:
        logger.warning(
            "The following required Volumes are not mounted: %s" % missing_volumes
        )
        title = "WARNING!"
        message = (
            "These required Volumes are not mounted...\n\n %s\n\nWould you like to try "
            "and mount the missing Volume(s)?" % "\n".join(missing_volumes)
        )
        retval = message_box.display(title, message)
        if retval == QtGui.QMessageBox.Cancel:
            logger.warning("User decided to cancel. Exiting.")
            return False
        else:
            for volume in missing_volumes:
                logger.info("Attempting to mount Volume %s" % volume)
                mount_volume(volume)
        # validate they're mounted now
        for volume in missing_volumes:
            if not is_mounted(volume):
                logger.error(
                    "Volume %s did not mount despite our best attempts" % volume
                )
                title = "ERROR!"
                message = (
                    "The Volume %s still did not mount. Please ensure you're connected to the VPN.\n"
                    "Aborting, sorry." % volume
                )
                retval = message_box.display(title, message)
                return False

    logger.info("All required Volumes are mounted.")
    return True
