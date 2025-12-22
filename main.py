import json
import subprocess
from pathlib import Path
from frontend.repoParser import clone_repo, remove_repo_path
from frontend.usageScanner import scan_and_filter_repo, trimmer, attach_asts_to_results
from frontend.utils import generate_cbom_from_ast, read_json_file
from backend.queries import clear_database

TEMP_ROOT = Path(__file__).resolve().parent / "results"
print(TEMP_ROOT)

url = "https://github.com/editorconfig/editorconfig-core-js.git"
url2 = "https://github.com/google/adk-js.git"
out = f"{TEMP_ROOT}/matches.json"

if __name__ == "__main__":
    repo_path = None
    try:
        print("Clearing database...")
        clear_database()
        repo_path, project_id = clone_repo(url2)
        print("Repo cloned at:", repo_path)
        result = scan_and_filter_repo(repo_path)
        print("Kept files after initial scan:", len(result["kept"]))
        print("Deleted files after initial scan:", len(result["deleted"]))

        trimRes = trimmer(repo_path, project_id)
        print("Kept files after trimming:", len(trimRes["kept_crypto_files"]))
        print("Deleted files after trimming:", len(trimRes["removed_non_crypto_files"]))
        print("Matches by category", trimRes["matches_by_category"])

        with open(out, "w") as f:
            json.dump(trimRes["matches_by_category"], f, indent=4)

        ast_output = attach_asts_to_results(out, trimRes["kept_crypto_files"])
        print("AST annotation complete:", ast_output)

        pruner_script = Path(__file__).resolve().parent / "frontend" / "pruneAst.js"

        try:
            pruned = subprocess.check_output(["node", str(pruner_script)], text=True)
            print("Pruning complete:", pruned)
        except subprocess.CalledProcessError as e:
            print("Pruning failed:", e.stdout, e.stderr)

        print ("Generating CBOMs...")
        fileJson = read_json_file(f"{TEMP_ROOT}/pruned_project_asts.json")
        if fileJson is None:
            raise ValueError("Failed to read pruned AST JSON file.")

        astJsonList = fileJson["files"]
        flat = [item for sub in astJsonList for item in sub]
        res = []
        for item in flat:
            if not isinstance(item, str):
                print("Skipping non-string AST item:", item)
                continue
            if isinstance(item, str):
                cbom = generate_cbom_from_ast(
                    ast_json_str=item,
                    model="gpt-4.1-mini"
                )
                print("Generated CBOM:", cbom)
                res.append(cbom)
        print("CBOM generation complete:", res)
        with open(f"{TEMP_ROOT}/cbom_output.json", "w") as f:
            json.dump(res, f, indent=4)

    except Exception as err:
        print("Error in main:", err)

    finally:
        if not repo_path:
            exit()
        remove_repo_path(repo_path.parent)
