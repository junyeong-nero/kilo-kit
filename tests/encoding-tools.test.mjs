import test from "node:test"
import assert from "node:assert/strict"
import { mkdtemp, mkdir, symlink, copyFile, readFile, writeFile, rm, realpath } from "node:fs/promises"
import { spawnSync } from "node:child_process"
import os from "node:os"
import path from "node:path"
import EncodingTools from "../tools/encoding/index.js"

async function fixture(t) {
  const directory = await realpath(await mkdtemp(path.join(os.tmpdir(), "encoding test 한글 ")))
  t.after(() => rm(directory, { recursive: true, force: true }))
  const python = spawnSync(process.platform === "win32" ? "python" : "python3", ["-c", "import sys; print(sys.executable)"], { encoding: "utf8" })
  assert.equal(python.status, 0, python.stderr)
  const exe = python.stdout.trim()
  await mkdir(path.join(directory, "runtime", "opencode-tools"), { recursive: true })
  if (process.platform === "win32") {
    await symlink(path.dirname(exe), path.join(directory, "runtime", "python"), "junction")
  } else {
    await mkdir(path.join(directory, "runtime", "python"))
    await symlink(exe, path.join(directory, "runtime", "python", "python.exe"))
  }
  await copyFile(new URL("../tools/encoding/file_io.py", import.meta.url), path.join(directory, "runtime", "opencode-tools", "file_io.py"))
  process.env.OPENCODE_KIT_HOME = directory
  const plugin = await EncodingTools()
  const project = path.join(directory, "project")
  await mkdir(project)
  const file = path.join(project, "sample.cpp")
  await writeFile(file, "before\r\n")
  const approvals = []
  const context = {
    directory: project, worktree: project, abort: new AbortController().signal,
    ask: async request => { approvals.push(request) },
  }
  return { plugin, project, directory, file, approvals, context }
}

test("read/edit/write replacements and aliases retain explicit approval", async t => {
  const { plugin, file, approvals, context } = await fixture(t)
  assert.equal(plugin.tool.edit, plugin.tool.encoding_edit)
  assert.equal(plugin.tool.write, plugin.tool.encoding_write)
  const result = await plugin.tool.edit.execute({ filePath: file, oldString: "before", newString: "after" }, context)
  assert.equal(await readFile(file, "utf8"), "after\r\n")
  assert.deepEqual(approvals.map(a => a.permission), ["read", "edit"])
  assert.match(approvals[1].metadata.diff, /before/)
  assert.match(result.metadata.diff, /after/)
  await assert.rejects(plugin["tool.execute.before"]({ tool: "apply_patch" }), /bypasses/)
})

test("denied edit leaves original bytes intact", async t => {
  const { plugin, file, context } = await fixture(t)
  context.ask = async request => { if (request.permission === "edit") throw new Error("denied") }
  await assert.rejects(plugin.tool.edit.execute({ filePath: file, oldString: "before", newString: "after" }, context), /denied/)
  assert.equal(await readFile(file, "utf8"), "before\r\n")
})

test("external file requires external-directory approval before read", async t => {
  const { plugin, directory, approvals, context } = await fixture(t)
  const external = path.join(directory, "outside.txt")
  await writeFile(external, "outside")
  await plugin.tool.read.execute({ filePath: external }, context)
  assert.deepEqual(approvals.map(a => a.permission), ["external_directory", "read"])
})

test("changes made while approval is pending are not overwritten", async t => {
  const { plugin, file, context } = await fixture(t)
  context.ask = async request => { if (request.permission === "edit") await writeFile(file, "IDE change") }
  await assert.rejects(plugin.tool.edit.execute({ filePath: file, oldString: "before", newString: "after" }, context), /changed/)
  assert.equal(await readFile(file, "utf8"), "IDE change")
})

test("non-Git global worktree uses session directory rules", async t => {
  const { plugin, project, file, context } = await fixture(t)
  context.worktree = "/"
  await writeFile(path.join(project, "encoding-rules.json"), JSON.stringify({ rules: [{ pattern: "*.cpp", encoding: "cp949" }] }))
  const result = await plugin.tool.read.execute({ filePath: file }, context)
  assert.equal(result.metadata.encoding, "cp949")
})
