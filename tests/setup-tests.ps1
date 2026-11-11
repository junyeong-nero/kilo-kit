# Isolated tests of the setup dependency copy; never run the system/provider setup body.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'scripts/setup.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$functions = @('Read-Json', 'Write-Text', 'Install-File', 'Install-OpenCodeDependencies')
foreach ($name in $functions) {
    $function = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true)
    if (-not $function) { throw "Missing function: $name" }
    Invoke-Expression $function.Extent.Text
}
$utf8 = New-Object Text.UTF8Encoding($false)
$toolRuntime = Join-Path $root 'tools/encoding'
$temp = Join-Path ([IO.Path]::GetTempPath()) ('opencode setup test ' + [guid]::NewGuid().ToString('N'))
try {
    $destination = Join-Path $temp 'clean profile'
    Install-OpenCodeDependencies $destination
    Install-OpenCodeDependencies $destination
    $entry = Join-Path $destination 'node_modules/@opencode-ai/plugin/dist/index.js'
    if (-not (Test-Path -LiteralPath $entry)) { throw 'Dependency copy failed.' }
    if (Test-Path -LiteralPath (Join-Path $destination 'node_modules/node_modules')) { throw 'Repeated setup nested node_modules.' }
    Remove-Item -LiteralPath (Join-Path $destination 'opencode-kit-dependencies.json')
    Install-OpenCodeDependencies $destination
    if (Test-Path -LiteralPath (Join-Path $destination 'opencode-kit-dependencies.json')) { throw 'Compatible unmanaged install was taken over.' }
    $conflict = Join-Path $temp 'unmanaged'
    Write-Text (Join-Path $conflict 'package.json') '{"dependencies":{"my-plugin":"1.0.0"}}'
    $blocked = $false
    try { Install-OpenCodeDependencies $conflict } catch {
        if ($_.Exception.Message -notmatch 'not managed') { throw }
        $blocked = $true
    }
    if (-not $blocked) { throw 'Unmanaged dependencies were overwritten.' }
    if ((Read-Json (Join-Path $conflict 'package.json')).dependencies.'my-plugin' -ne '1.0.0') { throw 'User package was modified.' }
    $template = Read-Json (Join-Path $root 'config/opencode.template.json')
    if ($template.permission.apply_patch -ne 'deny' -or $template.permission.edit -ne 'ask') { throw 'Unsafe file tool permissions.' }
    Write-Host 'SETUP_DEPENDENCIES_OK'
} finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
