# Isolated key migration tests; never run machine/provider setup here.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'scripts/setup.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
foreach ($name in @('Read-Json', 'Write-Text', 'Install-File', 'Resolve-ApiKeySetting')) {
    $function = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true)
    if (-not $function) { throw "Missing function: $name" }
    Invoke-Expression $function.Extent.Text
}
$utf8 = New-Object Text.UTF8Encoding($false)
$temp = Join-Path ([IO.Path]::GetTempPath()) ('kilo-setup-test-' + [guid]::NewGuid().ToString('N'))
try {
    $normal = Resolve-ApiKeySetting 'CUSTOM_KEY'
    if ($normal.Name -ne 'CUSTOM_KEY' -or $normal.InlineKey) { throw 'Variable name was misread as a key.' }
    if ((Resolve-ApiKeySetting '').Name -ne 'CORP_LLM_API_KEY') { throw 'Default key variable changed.' }
    $key = 'sk-123123123'
    $migrated = Resolve-ApiKeySetting $key
    if ($migrated.Name -ne 'CORP_LLM_API_KEY' -or $migrated.InlineKey -cne $key) { throw 'Literal key was altered or rejected.' }
    $blocked = $false
    try { Resolve-ApiKeySetting 'private.invalid-key' } catch {
        if ($_.Exception.Message.Contains('private.invalid-key')) { throw 'Invalid setting leaked into an error.' }
        $blocked = $true
    }
    if (-not $blocked) { throw 'Invalid variable name was accepted.' }
    $path = Join-Path $temp 'models.json'
    $registry = [pscustomobject]@{ provider = [pscustomobject]@{ apiKeyEnv = $key }; default = 'keep-model' }
    Write-Text $path ($registry | ConvertTo-Json)
    $registry.provider.apiKeyEnv = $migrated.Name
    $sanitized = $registry | ConvertTo-Json
    Install-File $path $sanitized -BackupText $sanitized
    foreach ($file in @($path, "$path.bak")) {
        if ([IO.File]::ReadAllText($file).Contains($key)) { throw 'Key leaked into registry or backup.' }
        if ((Read-Json $file).default -ne 'keep-model') { throw 'Model setting was lost.' }
    }
    Install-File $path ($sanitized + "`n")
    if ([IO.File]::ReadAllText("$path.bak").Contains($key)) { throw 'Repeated setup leaked the key.' }
    Write-Host 'SETUP_KEYS_OK'
} finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
