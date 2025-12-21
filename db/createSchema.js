import Database from "better-sqlite3";
import fs from "fs";
import path from "path";

const dbPath = path.resolve("pqc.db");

if (fs.existsSync(dbPath)) {
  fs.rmSync(dbPath);
  console.log("Old database removed.");
}

const db = new Database(dbPath);

db.pragma("journal_mode = WAL");
db.pragma("foreign_keys = ON");

console.log("Creating schema...");

db.exec(`
  CREATE TABLE project (
    projectId TEXT PRIMARY KEY,
    projectName TEXT NOT NULL
  );

  CREATE TABLE projectFile (
    fileId TEXT PRIMARY KEY,
    fileName TEXT NOT NULL,
    projectId TEXT NOT NULL,
    FOREIGN KEY (projectId) REFERENCES project(projectId) ON DELETE CASCADE
  );

  CREATE TABLE fileAST (
    astId TEXT PRIMARY KEY,
    fileId TEXT NOT NULL,
    ast TEXT NOT NULL, -- stores JSON
    FOREIGN KEY (fileId) REFERENCES projectFile(fileId) ON DELETE CASCADE
  );
`);

console.log("SQLite schema created successfully at:", dbPath);
db.close();
