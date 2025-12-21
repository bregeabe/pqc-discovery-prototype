import os
import re
from pathlib import Path
import json
import subprocess
from backend.queries import insert_file, insert_ast

KEEP_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}
IGNORE_FOLDERS = {"node_modules", "dist"}

CRYPTO_PATTERNS = {
    "aes": [
        r"\baes\b",
        r"aes-?\d+",
        r"AESKey",
        r"AES\.encrypt",
        r"AES\.decrypt",
    ],
    "rsa": [
        r"\brsa\b",
        r"rsa-?\d+",
        r"RSAPublicKey",
        r"RSAPrivateKey",
        r"RSAKey",
    ],
    "signing": [
        r"sign(ing)?",
        r"verify(ing)?",
        r"signature",
        r"digital[_ ]signature",
    ],
    "cert": [
        r"certificate",
        r"x\.509",
        r"public[_ ]?key",
        r"private[_ ]?key",
        r"pem",
        r"der",
    ],
    "hash": [
        r"sha-?\d+",
        r"hash",
        r"pbkdf2",
        r"scrypt",
        r"bcrypt",
        r"HMAC",
    ],
    "keys": [
        r"api[_ ]?key",
        r"secret",
        r"token",
    ]
}


def scan_and_filter_repo(repo_path: str | Path) -> dict:
    """
    Returns { kept: [...], deleted: [...] }
    """
    repo_path = Path(repo_path).resolve()

    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Invalid repo path: {repo_path}")

    kept_files = []
    deleted_files = []

    for root, _, files in os.walk(repo_path):
        root_path = Path(root)

        if any(ignore in root_path.parts for ignore in IGNORE_FOLDERS):
            continue

        for filename in files:
            file_path = root_path / filename
            extension = file_path.suffix.lower()

            if extension in KEEP_EXTENSIONS:
                kept_files.append(str(file_path))
            else:
                try:
                    file_path.unlink()
                    deleted_files.append(str(file_path))
                except Exception as e:
                    print(f"Warning: Failed to delete {file_path}: {e}")

    delete_empty_dirs(repo_path, IGNORE_FOLDERS)

    return {
        "kept": kept_files,
        "deleted": deleted_files
    }


def delete_empty_dirs(path: Path, ignore_folders: set[str]):
    """
    Recursively removes empty folders, except ignored ones.
    """
    for root, dirs, _ in os.walk(path, topdown=False):
        root_path = Path(root)

        if any(ignore in root_path.parts for ignore in ignore_folders):
            continue

        for d in dirs:
            dir_path = root_path / d

            if d in ignore_folders:
                continue

            try:
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
            except Exception as e:
                print(f"Warning: Failed to remove empty directory {dir_path}: {e}")


def trimmer(repo_path: str | Path, project_id: str) -> dict:
    """
    Reads all .js/.jsx/.ts/.tsx files, matches against crypto regex patterns,
    deletes non-matching files, and makes db record.

    Returns:
        {
            "kept_crypto_files": { file_path: { "categories": [...], "fileId": <uuid> } },
            "removed_non_crypto_files": [...],
            "matches_by_category": { category: [file_paths...] }
        }
    """
    repo_path = Path(repo_path).resolve()

    kept_by_file = {}          # file_path → { categories: [...], fileId: <uuid> }
    removed_files = []         # list of deleted files
    matches_by_category = {}   # category → [file_paths...]

    for category in CRYPTO_PATTERNS.keys():
        matches_by_category[category] = []

    compiled_patterns = [
        (category, re.compile(pattern, flags=re.IGNORECASE))
        for category, patterns in CRYPTO_PATTERNS.items()
        for pattern in patterns
    ]

    for root, _, files in os.walk(repo_path):
        root_path = Path(root)

        if any(ignore in root_path.parts for ignore in IGNORE_FOLDERS):
            continue

        for filename in files:
            file_path = root_path / filename

            if file_path.suffix.lower() not in KEEP_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(errors="ignore")
            except Exception:
                continue

            matched_categories = [
                category for category, regex in compiled_patterns if regex.search(content)
            ]

            if matched_categories:
                # Insert file record in SQLite
                file_id = insert_file(project_id, str(file_path))

                kept_by_file[str(file_path)] = {
                    "categories": matched_categories,
                    "fileId": file_id,
                }

                for category in matched_categories:
                    matches_by_category[category].append(str(file_path))

            else:
                try:
                    file_path.unlink()
                    removed_files.append(str(file_path))
                except Exception as e:
                    print(f"Warning: Failed to delete {file_path}: {e}")

    delete_empty_dirs(repo_path, IGNORE_FOLDERS)

    return {
        "kept_crypto_files": kept_by_file,
        "removed_non_crypto_files": removed_files,
        "matches_by_category": matches_by_category,
    }

def attach_asts_to_results(results_json_path: str | Path, kept_crypto_files: dict) -> dict:
    """
    Converts crypto file paths into ASTs and makes db record.

    kept_crypto_files format example:
    {
        "/path/to/file.ts": {
            "categories": ["aes", "rsa"],
            "fileId": "uuid4"
        }
    }

    Returns:
        {
            "files_annotated": <int>,
            "failures": <list>
        }
    """
    results_path = Path(results_json_path).resolve()

    results = json.loads(results_path.read_text())

    file_paths: set[str] = set()
    for category, files in results.items():
        if isinstance(files, list):
            for fp in files:
                file_paths.add(fp)

    script = Path(__file__).resolve().parent / "jsParser.js"

    failures = []
    inserted_count = 0

    for file_path in file_paths:
        if file_path not in kept_crypto_files:
            failures.append({
                "file_path": file_path,
                "error": "No fileId entry found"
            })
            continue

        fileId = kept_crypto_files[file_path]["fileId"]

        try:
            output = subprocess.check_output(
                ["node", str(script), file_path],
                text=True
            )
            ast_json = json.loads(output)

            insert_ast(fileId, json.dumps(ast_json))

            inserted_count += 1

        except Exception as e:
            failures.append({
                "file_path": file_path,
                "error": str(e)
            })

    return {
        "files_annotated": inserted_count,
        "failures": failures,
    }
