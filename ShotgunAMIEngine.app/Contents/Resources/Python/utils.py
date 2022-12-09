import os
import subprocess


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


def get_volume_name_from_path(path):
    if "production/post" in path.lower():
        return "production"
    if "droid3" in path.lower():
        return "droid3"
    if "droid2" in path.lower():
        return "droid2"
    # this is last because it exists in the above volume names
    if "droid" in path.lower():
        return "droid"


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


def check_missing_volume_mounts(volumes):
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
    return missing_volumes
