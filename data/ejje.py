import shutil

if shutil.which("ffmpeg") is None:
    raise RuntimeError("❌ ffmpeg no se encuentra en el PATH")
