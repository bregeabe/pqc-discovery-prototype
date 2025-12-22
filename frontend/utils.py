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


DEFAULT_MODEL = "gpt-4.1-mini"

SUPPORTED_MODELS = {
    "gpt-4.1-mini": "chat.completions",
    "gpt-4.1": "chat.completions",
    "gpt-4.1-turbo": "chat.completions",
    "o3-mini": "chat.completions",
    "o3": "chat.completions",
}

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
    MAX_CHARS: int = 120_000,
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
    - line_number: The line number in the source code file where the cryptographic element is found.
    - api_call: The specific API call or function used for the cryptographic operation (e.g. hashSync(data, salt), encrypt(data, key)).
    - algorithm: The cryptography algorithm being used (e.g., AES, 3DES, SHA-256, etc.)
    - cryptographic_function: The type of cryptographic function being performed (e.g. keygen, digest, verify)
    - mode: The mode of operation for the algorithm (e.g., CBC, GCM, ECB, etc.), if applicable.
    - key_size: The size of the cryptographic key in bits (e.g., 128, 256), if applicable.
    - purpose: A brief description of the purpose of the cryptographic operation (e.g., data encryption, password hashing).
    - multiple_uses: A boolean flag indicating whether multiple cryptographic uses were detected in the AST.
    Only provide the CBOM in json format.
    """

    if len(ast_json_str) > MAX_CHARS:
        print("AST too large, slicing:", len(ast_json_str))
        ast_json_str = ast_json_str[:MAX_CHARS]

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
                raise e

    raise RuntimeError("Max retries exceeded")

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
