# CI only: a disposable Windows runner, relocated bundle, empty profile and blocked OpenCode egress.
param([Parameter(Mandatory=$true)][string]$Bundle)
$ErrorActionPreference = 'Stop'
$utf8 = New-Object Text.UTF8Encoding($false)
$profile = Join-Path $env:RUNNER_TEMP ('opencode-profile-' + [guid]::NewGuid().ToString('N'))
$env:XDG_CONFIG_HOME = Join-Path $profile 'config'
$env:XDG_CACHE_HOME = Join-Path $profile 'cache'
$env:XDG_DATA_HOME = Join-Path $profile 'data'
$env:XDG_STATE_HOME = Join-Path $profile 'state'
$project = Join-Path $profile 'project'
New-Item -ItemType Directory -Force -Path $project | Out-Null
$registry = @{
    provider = @{ id = 'corp'; name = 'Smoke test'; baseUrl = 'http://127.0.0.1:1/v1'; apiKeyEnv = 'sk-ci-placeholder' }
    default = 'kit-smoke'
    models = @(@{ id = 'kit-smoke'; contextWindow = 8192; maxTokens = 1024; imageInput = $true })
}
[IO.File]::WriteAllText((Join-Path $Bundle 'config\models.json'), ($registry | ConvertTo-Json -Depth 8), $utf8)
# Reproduce a pre-existing incompatible default DB without touching real user data.
Remove-Item Env:OPENCODE_DB -ErrorAction SilentlyContinue
$dbDirectory = Join-Path $env:XDG_DATA_HOME 'opencode'
New-Item -ItemType Directory -Force -Path $dbDirectory | Out-Null
$oldDatabase = Join-Path $dbDirectory 'opencode.db'
& (Join-Path $Bundle 'runtime\python\python.exe') -I -B -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('CREATE TABLE interrupted_setup(id INTEGER)'); c.close()" $oldDatabase
if ($LASTEXITCODE) { throw 'Could not create incompatible DB fixture.' }
$oldHash = (Get-FileHash $oldDatabase).Hash
$command = Join-Path $Bundle 'bin\opencode.cmd'
$exe = Join-Path $Bundle 'bin\opencode\opencode.exe'
$rule = 'opencode-kit-ci-' + [guid]::NewGuid().ToString('N')
New-NetFirewallRule -DisplayName $rule -Direction Outbound -Program $exe -Action Block -Profile Any | Out-Null
Push-Location $project
try {
    # First DB initialization also runs under blocked OpenCode egress, not just --version/config.
    # The unreachable loopback API exercises saved-model fallback, not inference.
    & (Join-Path $Bundle 'setup.ps1') -NonInteractive
    foreach ($file in @('models.json', 'models.json.bak')) {
        $text = [IO.File]::ReadAllText((Join-Path $Bundle "config\$file"), $utf8)
        if ($text.Contains('sk-ci-placeholder')) { throw 'Inline API key leaked to registry or backup.' }
        if (($text | ConvertFrom-Json).provider.apiKeyEnv -ne 'CORP_LLM_API_KEY') { throw 'Key variable was not normalized.' }
    }
    if ([Environment]::GetEnvironmentVariable('CORP_LLM_API_KEY', 'Machine') -cne 'sk-ci-placeholder') { throw 'Inline key was not registered exactly.' }
    & $command session list --format json
    if ($LASTEXITCODE) { throw 'Session database could not be opened.' }
    if ((Get-FileHash $oldDatabase).Hash -ne $oldHash) { throw 'Existing default database was modified.' }
    $dbPath = (& $command db path | Out-String).Trim()
    if ($LASTEXITCODE -or (Split-Path $dbPath -Leaf) -ne 'opencode-kit.db') { throw 'Kit database isolation did not apply.' }
    if (-not (Test-Path -LiteralPath $dbPath)) { throw 'Kit database was not created.' }
    & $command --version
    if ($LASTEXITCODE) { throw 'OpenCode version check failed.' }
    # Do not invoke desktop MCP tools on the runner. These are imported separately during packaging.
    $configPath = Join-Path $env:XDG_CONFIG_HOME 'opencode\opencode.json'
    $config = [IO.File]::ReadAllText($configPath, $utf8) | ConvertFrom-Json
    foreach ($property in $config.mcp.PSObject.Properties) { $property.Value.enabled = $false }
    [IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 20), $utf8)
    $beforeLock = Get-FileHash (Join-Path $env:XDG_CONFIG_HOME 'opencode\package-lock.json')
    $resolved = (& $command debug config | Out-String)
    if ($LASTEXITCODE) { throw 'OpenCode config initialization failed.' }
    $parsed = $resolved | ConvertFrom-Json
    if ($parsed.model -ne 'corp/kit-smoke') { throw 'Custom provider/model did not load.' }
    $agent = (& $command debug agent build | Out-String)
    if ($LASTEXITCODE) { throw 'OpenCode tool initialization failed.' }
    $tools = ($agent | ConvertFrom-Json).tools
    foreach ($name in @('encoding_read', 'encoding_edit', 'encoding_write')) {
        if ($tools.$name -ne $true) { throw "Encoding tool not available: $name" }
    }
    if ($tools.apply_patch -eq $true) { throw 'apply_patch bypass is enabled.' }
    $afterLock = Get-FileHash (Join-Path $env:XDG_CONFIG_HOME 'opencode\package-lock.json')
    if ($beforeLock.Hash -ne $afterLock.Hash) { throw 'OpenCode changed preinstalled dependencies during first startup.' }
    Write-Host 'OFFLINE_DATABASE_KEYS_CONFIG_AND_TOOLS_OK (no model inference or desktop UI test)'
} finally {
    Pop-Location
    Remove-NetFirewallRule -DisplayName $rule
}
