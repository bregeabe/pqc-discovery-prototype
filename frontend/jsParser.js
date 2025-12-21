import * as swc from "@swc/core";
import * as fs from "fs";

async function parseFileToAst(path) {
  const code = fs.readFileSync(path, "utf-8");

  try {
    const ast = await swc.parse(code, {
      syntax: "typescript",
      tsx: path.endsWith(".tsx"),
      jsx: path.endsWith(".jsx"),
      decorators: true,
      comments: true,
      target: "es2022",
    });

    return { ok: true, ast };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

(async () => {
  const file = process.argv[2];
  const result = await parseFileToAst(file);
  console.log(JSON.stringify(result));
})();
