# Isolated setup function tests; never run the system/provider setup body.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'scripts/setup.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$functions = @('Read-Json', 'Write-Text', 'Install-File', 'Install-OpenCodeDependencies', 'Resolve-ApiKeySetting')
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
    $normal = Resolve-ApiKeySetting 'CUSTOM_KEY'
    if ($normal.Name -ne 'CUSTOM_KEY' -or $normal.InlineKey) { throw 'Environment variable name was misread as a key.' }
    if ((Resolve-ApiKeySetting '').Name -ne 'CORP_LLM_API_KEY') { throw 'Default key variable changed.' }
    $key = 'sk-123123123'
    $migrated = Resolve-ApiKeySetting $key
    if ($migrated.Name -ne 'CORP_LLM_API_KEY' -or $migrated.InlineKey -cne $key) { throw 'Literal sk- key was altered or rejected.' }
    $blocked = $false
    try { Resolve-ApiKeySetting 'private.invalid-key' } catch {
        if ($_.Exception.Message.Contains('private.invalid-key')) { throw 'Invalid setting leaked into an error.' }
        $blocked = $true
    }
    if (-not $blocked) { throw 'Invalid variable name was accepted.' }
    $registryPath = Join-Path $temp 'models.json'
    $registry = [pscustomobject]@{ provider = [pscustomobject]@{ apiKeyEnv = $key }; default = 'keep-model' }
    Write-Text $registryPath ($registry | ConvertTo-Json)
    $registry.provider.apiKeyEnv = $migrated.Name
    $sanitized = $registry | ConvertTo-Json
    Install-File $registryPath $sanitized -BackupText $sanitized
    foreach ($path in @($registryPath, "$registryPath.bak")) {
        if ([IO.File]::ReadAllText($path).Contains($key)) { throw 'Migrated key leaked into registry or backup.' }
        if ((Read-Json $path).default -ne 'keep-model') { throw 'Model setting was lost during key migration.' }
    }
    Install-File $registryPath ($sanitized + "`n")
    if ([IO.File]::ReadAllText("$registryPath.bak").Contains($key)) { throw 'Repeated setup leaked the key.' }
    Write-Host 'SETUP_DEPENDENCIES_AND_KEYS_OK'
} finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
