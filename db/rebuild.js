import { execSync } from "child_process";
import path from "path";

const createPath = path.resolve("db/createSchema.js");

console.log("Rebuilding SQLite database...");
execSync(`node ${createPath}`, { stdio: "inherit" });
console.log("Database rebuilt.");
