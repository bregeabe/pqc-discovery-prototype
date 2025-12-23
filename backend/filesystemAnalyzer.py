import os
import stat
import json
import time
from pathlib import Path
from typing import Dict, List


def safe_stat(path: Path):
    try:
        return path.lstat()
    except Exception:
        return None


def file_metadata(path: Path) -> Dict:
    st = safe_stat(path)
    if not st:
        return {}

    is_symlink = path.is_symlink()

    metadata = {
        "path": str(path.resolve(strict=False)),
        "name": path.name,
        "extension": path.suffix.lower(),
        "type": (
            "symlink" if is_symlink
            else "directory" if stat.S_ISDIR(st.st_mode)
            else "file"
        ),
        "size_bytes": st.st_size,
        "timestamps": {
            "created": st.st_ctime,
            "modified": st.st_mtime,
            "accessed": st.st_atime,
        },
        "permissions": {
            "mode": oct(st.st_mode & 0o777),
            "is_executable": bool(st.st_mode & stat.S_IXUSR),
        },
        "ownership": {
            "uid": getattr(st, "st_uid", None),
            "gid": getattr(st, "st_gid", None),
        },
        "filesystem": {
            "inode": getattr(st, "st_ino", None),
            "device": getattr(st, "st_dev", None),
        },
        "symlink_target": (
            os.readlink(path) if is_symlink else None
        ),
    }

    return metadata


def scan_filesystem(
    root: str,
    follow_symlinks: bool = False
) -> List[Dict]:
    results = []
    root_path = Path(root)

    for dirpath, dirnames, filenames in os.walk(
        root_path,
        followlinks=follow_symlinks
    ):
        dirpath = Path(dirpath)

        dir_meta = file_metadata(dirpath)
        if dir_meta:
            results.append(dir_meta)

        for name in filenames:
            file_path = dirpath / name
            meta = file_metadata(file_path)
            if meta:
                results.append(meta)

    return results


def main():
    root = "."
    output_file = "results/filesystem_inventory.json"

    inventory = {
        "scan_root": root,
        "scan_time": time.time(),
        "entries": scan_filesystem(root)
    }

    with open(output_file, "w") as f:
        json.dump(inventory, f, indent=2)

    print(f"Scan complete: {len(inventory['entries'])} entries")


if __name__ == "__main__":
    main()
