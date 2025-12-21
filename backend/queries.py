import sqlite3
from uuid import uuid4
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "pqc.db"


def insert_project(project_name: str) -> str:
    """
    Inserts a new project row into SQLite and returns the projectId (UUID).
    """
    project_id = str(uuid4())

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO project (projectId, projectName) VALUES (?, ?)",
        (project_id, project_name)
    )

    conn.commit()
    conn.close()

    return project_id


def insert_file(project_id: str, file_name: str) -> str:
    """
    Inserts a projectFile row and returns fileId (UUID).
    """
    file_id = str(uuid4())

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO projectFile (fileId, fileName, projectId) VALUES (?, ?, ?)",
        (file_id, file_name, project_id)
    )

    conn.commit()
    conn.close()

    return file_id


def insert_ast(file_id: str, ast_json_string: str) -> str:
    """
    Inserts an AST entry into fileAST table and returns astId (UUID).
    """
    ast_id = str(uuid4())

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO fileAST (astId, fileId, ast) VALUES (?, ?, ?)",
        (ast_id, file_id, ast_json_string)
    )

    conn.commit()
    conn.close()

    return ast_id


def get_project_files(project_id: str) -> list[tuple]:
    """
    Returns (fileId, fileName) rows linked to a project.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT fileId, fileName FROM projectFile WHERE projectId = ?",
        (project_id,)
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_project_asts(project_id: str) -> list[tuple]:
    """
    Returns ASTs for a project with filename included.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            fileAST.astId,
            fileAST.ast,
            projectFile.fileName
        FROM fileAST
        JOIN projectFile ON fileAST.fileId = projectFile.fileId
        WHERE projectFile.projectId = ?
        """,
        (project_id,)
    )

    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_project(project_id: str) -> None:
    """
    Deletes a project and cascades deletes files + ASTs.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM project WHERE projectId = ?", (project_id,))

    conn.commit()
    conn.close()

def clear_database() -> None:
    """
    Deletes all rows from project, projectFile, and fileAST tables.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = OFF;")

    cursor.execute("DELETE FROM fileAST;")
    cursor.execute("DELETE FROM projectFile;")
    cursor.execute("DELETE FROM project;")

    cursor.execute("PRAGMA foreign_keys = ON;")

    conn.commit()
    conn.close()
