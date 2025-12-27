import ast
import json
import gzip
from pathlib import Path
from backend.queries import get_project_asts, DB_PATH
from typing import List, Union, Optional, Literal, Dict, Any
from openai import OpenAI
import json
import os
import logging
import time
from dotenv import load_dotenv
import os
from backend.queries import clear_database
from frontend.usageScanner import scan_and_filter_repo, trimmer, attach_asts_to_results, resolve_imports_for_repo
from frontend.repoParser import clone_repo, remove_repo_path
import subprocess
import re

load_dotenv()

DEFAULT_MODEL = "gpt-4.1-mini"

SUPPORTED_MODELS = {
    "gpt-4.1-mini": "chat.completions",
    "gpt-4.1": "chat.completions",
    "gpt-4.1-turbo": "chat.completions",
    "o3-mini": "chat.completions",
    "o3": "chat.completions",
}
TEMP_ROOT = Path(__file__).resolve().parent.parent / "results"

def export_all_asts_to_json(project_id: str, output_path: str | Path) -> dict:
    """
    Loads all fileAST rows from SQLite and writes a single JSON export file.

    Also computes:
      - total original size
      - total pruned size
      - % size saved
      - gzipped size comparison
    """

    rows = get_project_asts(project_id)

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export = {
        "database": str(DB_PATH),
        "total_files": len(rows),
        "files": rows,
    }

    raw_json = json.dumps(export, indent=2)
    output_path.write_text(raw_json, encoding="utf8")

    return {
        "json_output": raw_json,
        "total_files": len(rows),
    }

# if __name__ == "__main__":
#     export_all_asts_to_json("d487a961-e62e-4094-9caa-a4cb1a13a25d", "./results/pruned_project_asts.json")

def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def _run_chat_completion(
    model: str,
    prompt: str,
    response_mode: Literal["json", "text"],
) -> Union[str, Dict[str, Any]]:
    client = _get_client()

    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Model {model} not supported")

    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    content = completion.choices[0].message.content or ""

    if response_mode == "text":
        return content

    return {
        "model": model,
        "input": prompt,
        "output": content,
        "raw": completion.to_dict()
    }


def run_openai_query(
    input_data: Union[str, List[str]],
    model: str = DEFAULT_MODEL,
    response_mode: Literal["json", "text"] = "json",
) -> Union[None, str, Dict[str, Any]]:
    if isinstance(input_data, str):
        return _run_chat_completion(
            model=model,
            prompt=input_data,
            response_mode=response_mode
        )

def generate_cbom_from_ast(
    ast_json_str: str,
    model: str = DEFAULT_MODEL,
) -> Optional[Any]:
    BASE_PROMPT = """
    You will receive an AST in JSON format representing source code files with some type of cryptographic use.
    Your task is to analyze the AST and generate a comprehensive Cryptographic Bill of Materials (CBOM) that details all cryptographic components found within the code.
    Please provide the CBOM in JSON format with the following structure:
    {
        file_name: <string> | null,
        line_number: <int> | null,
        api_call: <string> | null,
        algorithm: <string> | null,
        cryptographic_function: <string> | null,
        mode: <string> | null,
        key_size: <int> | null,
        purpose: <string> | null,
        multiple_uses: <boolean>
    }
    Ensure that each entry in the CBOM corresponds to a distinct cryptographic element identified in the AST.
    Also note that there could be more than one use of cryptography in a single AST.
    If this is the case, simply pick the first one and set the flag "multiple_uses": true in the output.
    Here is a short description of each field:
    - file_name: The name of the source code file where the cryptographic element is located.
    - line_number: The line number in the source code file where the API call is made.
    - api_call: The specific API call or function used for the cryptographic operation (e.g. hashSync(data, salt), encrypt(data, key)).
    - algorithm: The cryptography algorithm being used (e.g., AES, 3DES, SHA-256, etc.)
    - cryptographic_function: The type of cryptographic function being performed (e.g. keygen, digest, verify)
    - mode: The mode of operation for the algorithm (e.g., CBC, GCM, ECB, etc.), if applicable.
    - key_size: The size of the cryptographic key in bits (e.g., 128, 256), if applicable.
    - purpose: A brief description of the purpose of the cryptographic operation (e.g., data encryption, password hashing).
    - multiple_uses: A boolean flag indicating whether multiple cryptographic uses were detected in the AST.
    Only provide the CBOM in json format.
    """

    prompt = BASE_PROMPT + ast_json_str

    for attempt in range(1,6):
        try:
            return run_openai_query(
                input_data=prompt,
                model=model,
                response_mode="json"
            )
        except Exception as e:
            if "429" in str(e):
                wait = attempt * 2
                print(f"Rate limit hit, retrying in {wait}s...")
                time.sleep(wait)
            else:
                return {"error": str(e)}

    # raise RuntimeError("Max retries exceeded")
    print("skipping after max retries")

def read_json_file(file_path: str) -> Optional[Any]:
    """
    Reads a JSON file and returns the parsed data.

    Args:
        file_path (str): Absolute or relative path to the JSON file.

    Returns:
        Any: Parsed JSON content (dict, list, etc.) or None if file doesn't exist or fails to parse.
    """
    if not os.path.exists(file_path):
        logging.warning(f"JSON file not found: {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON file {file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error reading JSON file {file_path}: {e}")
    return None

def parse_github_repo(github_url: str, out_path: str ) -> tuple[Dict[Any, Any], str, Path]:
        print("Clearing database...")
        clear_database()
        repo_path, project_id = clone_repo(github_url)
        print("Repo cloned at:", repo_path)
        result = scan_and_filter_repo(repo_path)
        print("Kept files after initial scan:", len(result["kept"]))
        print("Deleted files after initial scan:", result["deleted"])

        print("Resolving imports...")
        resolve_imports_for_repo(repo_path)

        print("Trimming non-crypto files...")
        trimRes = trimmer(repo_path, project_id)
        print("Kept files after trimming:", len(trimRes["kept_crypto_files"]))
        print("Deleted files after trimming:", len(trimRes["removed_non_crypto_files"]))
        print("Matches by category", trimRes["matches_by_category"])

        with open(out_path, "w") as f:
            json.dump(trimRes["matches_by_category"], f, indent=4)

        ast_output = attach_asts_to_results(out_path, trimRes["kept_crypto_files"])
        return (ast_output, project_id, repo_path)

def prune_ast( project_id: str) -> Path:
        pruner_script = Path(__file__).resolve().parent.parent / "frontend" / "pruneAst.js"

        try:
            pruned = subprocess.check_output(["node", str(pruner_script)], text=True)
            print("Pruning complete:", pruned)
        except subprocess.CalledProcessError as e:
            print("Pruning failed:", e.stdout, e.stderr)

        export_all_asts_to_json(project_id, f"{TEMP_ROOT}/pruned_project_asts.json")
        return TEMP_ROOT / "pruned_project_asts.json"

def collect_unique_files(matches: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Returns a mapping:
      file_path -> [categories...]
    """
    file_map: Dict[str, List[str]] = {}

    for category, files in matches.items():
        for f in files:
            file_map.setdefault(f, []).append(category)

    return file_map


def read_source_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logging.warning(f"Failed to read {path}: {e}")
        return None


def generate_cboms_from_matches(MATCHES_FILE: Path = TEMP_ROOT / "matches.json", OUTPUT_FILE: Path = TEMP_ROOT / "cbom_output.json"):
    matches = read_json_file(str(MATCHES_FILE))
    if not matches:
        raise ValueError("matches.json is missing or empty")

    file_map = collect_unique_files(matches)

    logging.info(f"Total unique files to process: {len(file_map)}")

    results: List[Dict[str, Any]] = []

    for idx, (file_path, categories) in enumerate(file_map.items(), start=1):
        path = Path(file_path)

        logging.info(f"[{idx}/{len(file_map)}] Processing {path}")

        source = read_source_file(path)
        if not source:
            continue
        # print(source[:100000])
        try:
            cbom = generate_cbom_from_ast(
                ast_json_str=f"FILENAME: {path}\n SOURCE: {source}",
                model="gpt-4.1",
            )
        except Exception as e:
            logging.error(f"CBOM generation failed for {path}: {e}")
            continue

        results.append({
            "file_path": str(path),
            "categories": categories,
            "cbom": cbom,
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")

    logging.info(f"CBOM generation complete → {OUTPUT_FILE}")

def generate_cboms_from_ast_files(out_ast_path: Path = TEMP_ROOT / "pruned_project_asts.json"):
    print ("Generating CBOMs...")
    fileJson = read_json_file(str(out_ast_path))
    if fileJson is None:
        raise ValueError("Failed to read pruned AST JSON file.")

    astJsonList = fileJson["files"]
    flat = ["".join(sub) for sub in astJsonList]
    res = []
    PATH_RE = re.compile(r"(/Users/abrahambrege/.*?\.js)")
    for item in flat:
        if not isinstance(item, str):
            print("Skipping non-string AST item:", item)
            continue
        if isinstance(item, str):
            if len(item) > 120000:
                print("AST too large, using source code only...")
                if not PATH_RE.search(item):
                    print("Could not extract file path from AST, skipping...")
                    continue
                path_match = PATH_RE.search(item)
                if path_match is None:
                    print("Could not extract file path from AST, skipping...")
                    continue
                ast_json_str = read_source_file(Path(path_match.group(1)))
                if ast_json_str is None:
                    print("Could not read source file, skipping...")
                    continue
                cbom = generate_cbom_from_ast(
                    ast_json_str=ast_json_str,
                    model="gpt-4.1"
                )
                print("Generated CBOM from source file:", cbom)
                res.append(cbom)
                continue
            cbom = generate_cbom_from_ast(
                ast_json_str=item,
                model="gpt-4.1"
            )
            print("Generated CBOM:", cbom)
            res.append(cbom)
    print("CBOM generation complete:", res)
    with open(f"{TEMP_ROOT}/cbom_output.json", "w") as f:
        json.dump(res, f, indent=4)

def remove_empty_entries(source_file_path: Path, output_file_path: Path):
    data = read_json_file(str(source_file_path))
    if data is None:
        raise ValueError("Failed to read source JSON file.")

    for entry in data:
        cbom = entry.get("cbom", {})
        if isinstance(cbom, dict):
            entry["cbom"] = {k: v for k, v in cbom.items() if v not in (None, "", [], {})}
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    output_file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Filtered entries written to {output_file_path}, total: {len(data)}")