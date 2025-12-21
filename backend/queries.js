import { db } from "../db/client.js";
import { v4 as uuidv4 } from "uuid";

export function getProjectFiles(projectId) {
  return db.prepare(
    `SELECT fileId, fileName FROM projectFile WHERE projectId = ?`
  ).all(projectId);
}

export function getProjectASTs(projectId) {
  return db.prepare(
    `
    SELECT
      fileAST.astId,
      fileAST.ast,
      projectFile.fileName
    FROM fileAST
    JOIN projectFile ON fileAST.fileId = projectFile.fileId
    WHERE projectFile.projectId = ?
    `
  ).all(projectId);
}

export function insertProject(name) {
  const id = uuidv4();
  db.prepare(`INSERT INTO project (projectId, projectName) VALUES (?, ?)`)
    .run(id, name);
  return id;
}

export function insertFile(projectId, fileName) {
  const id = uuidv4();
  db.prepare(
    `INSERT INTO projectFile (fileId, fileName, projectId) VALUES (?, ?, ?)`
  ).run(id, fileName, projectId);
  return id;
}

export function insertAST(fileId, astJsonString) {
  const id = uuidv4();
  db.prepare(
    `INSERT INTO fileAST (astId, fileId, ast) VALUES (?, ?, ?)`
  ).run(id, fileId, astJsonString);
  return id;
}

export function deleteProject(projectId) {
  db.prepare(`DELETE FROM project WHERE projectId = ?`).run(projectId);
}
