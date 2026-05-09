import os
import hashlib
import subprocess
from flask import current_app


def get_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def convert_for_radio(input_path, output_path, artist=None, title=None, bitrate="128k"):
    tmp_path = output_path + ".tmp.mp3"
    cmd = [
        "ffmpeg",
        "-i",
        input_path,
        "-b:a",
        bitrate,
        "-map_metadata",
        "-1",
        "-y",
        tmp_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=60, check=True)
    if artist or title:
        cmd2 = ["ffmpeg", "-i", tmp_path, "-c", "copy"]
        if artist:
            cmd2 += ["-metadata", f"artist={artist}"]
        if title:
            cmd2 += ["-metadata", f"title={title}"]
        cmd2 += ["-y", output_path]
        subprocess.run(cmd2, capture_output=True, timeout=30, check=True)
        os.remove(tmp_path)
    else:
        os.rename(tmp_path, output_path)
    return True


def update_icecast_playlist(playlist_file, tracks):
    radio_folder = current_app.config.get("RADIO_FOLDER", "/root/deepchan/static/radio")
    with open(playlist_file, "w") as f:
        for track in tracks:
            if track.file_path and os.path.exists(track.file_path):
                rel_path = os.path.relpath(track.file_path, radio_folder)
                f.write(rel_path + "\n")
    subprocess.run(["/opt/deepchan/radio_control.sh", "reload"], capture_output=True)


def is_icecast_running():
    result = subprocess.run(["pgrep", "-f", "icecast2"], capture_output=True)
    return result.returncode == 0
