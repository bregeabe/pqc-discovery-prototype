import json
import subprocess
from pathlib import Path
from frontend.repoParser import clone_repo, remove_repo_path
from frontend.usageScanner import scan_and_filter_repo, trimmer, attach_asts_to_results
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

        # pruner_script = Path(__file__).resolve().parent / "frontend" / "pruneAst.js"

        # pruned = subprocess.check_output(
        #     ["node", str(pruner_script), ast_output["output_path"]],
        #     text=True
        # )

        # print("Pruning complete:", pruned)

    except Exception as err:
        print("Error in main:", err)

    finally:
        if not repo_path:
            exit()
        remove_repo_path(repo_path.parent)
