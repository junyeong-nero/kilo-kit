import { tool } from "@opencode-ai/plugin"
import { spawn } from "node:child_process"
import { lstat, realpath } from "node:fs/promises"
import path from "node:path"

export default async function EncodingTools() {
  const home = process.env.OPENCODE_KIT_HOME
  if (!home) throw new Error("OPENCODE_KIT_HOME is missing. Run opencode-kit setup.ps1.")
  const python = path.join(home, "runtime", "python", "python.exe")
  const script = path.join(home, "runtime", "opencode-tools", "file_io.py")

  function invoke(request, signal) {
    return new Promise((resolve, reject) => {
      const child = spawn(python, ["-I", "-X", "utf8", "-B", script], {
        stdio: ["pipe", "pipe", "pipe"], windowsHide: true, signal,
      })
      let stdout = "", stderr = ""
      child.stdout.setEncoding("utf8").on("data", data => { stdout += data })
      child.stderr.setEncoding("utf8").on("data", data => { stderr += data })
      child.on("error", reject)
      child.stdin.on("error", reject)
      child.on("close", code => {
        try {
          const result = JSON.parse(stdout)
          if (code !== 0 || result.error) throw new Error(result.error || stderr || "Encoding I/O failed")
          resolve(result)
        } catch (error) { reject(error) }
      })
      child.stdin.end(JSON.stringify(request))
    })
  }

  async function canonical(file) {
    try {
      if ((await lstat(file)).isSymbolicLink()) throw new Error("Symlink files are not supported.")
      return await realpath(file)
    } catch (error) {
      if (error.code !== "ENOENT") throw error
      const parent = path.dirname(file)
      if (parent === file) throw error
      return path.join(await canonical(parent), path.basename(file))
    }
  }

  async function execute(operation, args, context) {
    // OpenCode uses '/' as the global worktree for non-Git/SVN sessions.
    const worktree = context.worktree && path.resolve(context.worktree)
    const root = await realpath(worktree && worktree !== path.parse(worktree).root ? worktree : context.directory)
    const file = await canonical(path.resolve(context.directory, args.filePath))
    const relative = path.relative(root, file)
    if (relative === ".." || relative.startsWith(".." + path.sep) || path.isAbsolute(relative)) {
      await context.ask({ permission: "external_directory", patterns: [file], always: [file], metadata: { filepath: file } })
    }
    // Preserve read policies such as .env restrictions, including before a full-file replacement.
    await context.ask({ permission: "read", patterns: [relative], always: [relative], metadata: { filepath: file } })
    const prepared = await invoke({ ...args, action: "prepare", operation, root, filePath: file }, context.abort)
    if (operation === "read") return { title: file, output: prepared.output, metadata: { encoding: prepared.encoding } }
    await context.ask({
      permission: "edit", patterns: [relative], always: [relative],
      metadata: { filepath: file, diff: prepared.diff, encoding: prepared.encoding },
    })
    if (context.abort?.aborted) throw new Error("Cancelled before commit; file was not modified.")
    const saved = await invoke({ action: "commit", plan: prepared }, context.abort)
    return {
      title: file, output: saved.output,
      metadata: {
        diff: prepared.diff, encoding: prepared.encoding,
        filediff: { file, additions: prepared.added, deletions: prepared.removed },
      },
    }
  }

  const read = tool({
    description: "Read text with strict encoding preservation. Rules: encoding-rules.json at worktree root; otherwise BOM or valid UTF-8. Unknown legacy files are rejected. Directories can be listed. Binary/image files are not supported; use the relevant MCP for screenshots/documents.",
    args: {
      filePath: tool.schema.string(),
      offset: tool.schema.number().int().min(1).optional(),
      limit: tool.schema.number().int().min(1).max(2000).optional(),
    },
    execute: (args, context) => execute("read", args, context),
  })
  const edit = tool({
    description: "Exactly replace text while preserving encoding, BOM and line endings. Fails on unknown encoding, lossy conversion, ambiguous matches or concurrent changes. Use encoding_edit if edit is unavailable. Never use shell or apply_patch to bypass this tool.",
    args: {
      filePath: tool.schema.string(), oldString: tool.schema.string(), newString: tool.schema.string(),
      replaceAll: tool.schema.boolean().optional(),
    },
    execute: (args, context) => execute("edit", args, context),
  })
  const write = tool({
    description: "Write a complete text file preserving existing encoding/BOM/line endings; new files use a matching encoding-rules.json rule or UTF-8. Requests approval with a diff before writing. Use encoding_write if write is unavailable.",
    args: { filePath: tool.schema.string(), content: tool.schema.string() },
    execute: (args, context) => execute("write", args, context),
  })
  return {
    tool: { read, edit, write, encoding_read: read, encoding_edit: edit, encoding_write: write },
    "tool.execute.before": async input => {
      if (input.tool === "apply_patch") throw new Error("apply_patch bypasses encoding protection. Use edit/encoding_edit or write/encoding_write.")
    },
  }
}
