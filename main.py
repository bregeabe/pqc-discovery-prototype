import json
import subprocess
from pathlib import Path
from frontend.utils import parse_github_repo, prune_ast, generate_cboms_from_ast_files, generate_cboms_from_matches, clone_repo

TEMP_ROOT = Path(__file__).resolve().parent / "results"
print(TEMP_ROOT)

url = "https://github.com/juhoen/hybrid-crypto-js"
url2 = "https://github.com/google/adk-js.git"
out = f"{TEMP_ROOT}/matches.json"

if __name__ == "__main__":
    repo_path = None
    try:
        ast_output, project_id, repo_path = parse_github_repo(url, out)
        # clone_repo(url2)
        out_ast_path = prune_ast(project_id)
        # generate_cboms_from_ast_files(out_ast_path)
        generate_cboms_from_matches()

    except Exception as err:
        print("Error in main:", err)

    finally:
        if not repo_path:
            exit()
        # remove_repo_path(repo_path.parent)
