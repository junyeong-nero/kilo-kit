# One-time setup so `kilo` runs from any folder with the internal model API and the bundled MCP servers.
#   1. Register the provider (API base URL + key) and complete config\models.json from the API's /models list.
#   2. Install the Kilo config into %USERPROFILE%\.config\kilo (kilo.json, AGENTS.md) and ripgrep into Kilo's cache.
#   3. Set machine PATH (kilo, rg, fd) and variables (offline switches, API key, build center Redis credentials).
# Re-run after moving the bundle folder, or with -Reconfigure to change the provider.
# Keep this file ASCII: Windows PowerShell 5.1 reads BOM-less scripts in the system code page.
param(
    # Only check that the bundle is complete; change nothing.
    [switch]$Check,
    # Internal model API, OpenAI compatible (for example http://10.0.0.1:8000/v1).
    [string]$BaseUrl,
    # API key, stored as a system variable. Prefer the hidden prompt: a key typed here stays in shell history.
    [string]$ApiKey,
    # Default model ID. Otherwise the saved default, a menu, or the first chat model the API lists.
    [string]$Model,
    # Build center Redis credentials (REDISCLI_AUTH, HSC_REDIS_USERNAME). Optional.
    [string]$RedisPassword,
    [string]$RedisUsername,
    # Ask again for the provider, API key and Redis credentials.
    [switch]$Reconfigure,
    # Never prompt (CI, scripted installs). Missing required values fail with a message instead.
    [switch]$NonInteractive,
    # Internal: the elevated child changes machine settings only, never another account's user settings.
    [switch]$SystemOnly,
    [string]$SecretBlob
)
$ErrorActionPreference = 'Stop'
$utf8 = New-Object Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
# Windows PowerShell 5.1 may serialize arrays as {"value":[...],"Count":n} without this.
Remove-TypeData -TypeName System.Array -ErrorAction SilentlyContinue
$BundleRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$configDir = Join-Path $BundleRoot 'config'
$python = Join-Path $BundleRoot 'runtime\python\python.exe'
$kiloExe = Join-Path $BundleRoot 'bin\kilo\kilo.exe'

$required = @('bin\kilo\kilo.exe', 'bin\kilo\kilo-sandbox-mutation-worker.js', 'bin\kilo\tree-sitter\tree-sitter.wasm',
    'bin\kilo\tree-sitter\tree-sitter-cpp.wasm', 'bin\kilo\tree-sitter\tree-sitter-c_sharp.wasm', 'bin\rg.exe',
    'runtime\python\python.exe', 'runtime\python\python313.dll', 'runtime\python\python313.zip', 'runtime\python\python313._pth',
    'runtime\python\Lib\site-packages\redis\__init__.py', 'runtime\python\Lib\site-packages\mcp\__init__.py',
    'runtime\python\Lib\site-packages\tzdata\__init__.py', 'bin\fd.exe',
    'mcp\build-center\main.py', 'mcp\build-center\service.py',
    'config\kilo.template.json', 'config\models.example.json', 'config\AGENTS.md',
    'config\redis\settings.json', 'config\redis\server_IP_mappings.example.json', 'config\redis\owners.example.json',
    'third_party\kilo\LICENSE', 'third_party\python\PYTHON-LICENSE.txt', 'third_party\ripgrep\LICENSE-MIT', 'third_party\fd\LICENSE-MIT')
foreach ($item in $required) {
    $path = Join-Path $BundleRoot $item
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing bundle file: $item. Use the complete offline release ZIP." }
    if ($item.EndsWith('.exe') -and (Get-Item -LiteralPath $path).Length -lt 1024) {
        throw "Invalid executable: $item. Replace it with the official Windows executable."
    }
}
if ($Check) {
    Write-Host "Required files found: $BundleRoot"
    return
}

# Everything kilo needs before it reads its config is machine-wide: some PCs reset user variables at sign-in.
# These switches keep kilo from reaching the internet (model catalog, updates, telemetry, LSP/ripgrep downloads, sharing).
# bin holds rg.exe and fd.exe for the shell; bin\kilo holds kilo.exe.
$pathDirs = { param($root) @('bin\kilo', 'bin') | ForEach-Object { Join-Path $root $_ } }
$systemPathDirs = @(& $pathDirs $BundleRoot)
$machineVars = [ordered]@{
    KILO_KIT_HOME               = $BundleRoot
    KILO_DISABLE_AUTOUPDATE     = '1'
    KILO_DISABLE_MODELS_FETCH   = '1'
    KILO_DISABLE_LSP_DOWNLOAD   = '1'
    KILO_DISABLE_SHARE          = '1'
    KILO_DISABLE_SESSION_INGEST = '1'
    KILO_TELEMETRY_LEVEL        = 'off'
}
$envKeyPath = 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
function Get-MachinePath {
    # Raw value so entries such as %SystemRoot% stay unexpanded when written back.
    $value = [string][Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($envKeyPath).GetValue('Path', '', 'DoNotExpandEnvironmentNames')
    @($value.Split(';') | Where-Object { $_ } | ForEach-Object { $_.TrimEnd('\') })
}
function Test-SystemReady([System.Collections.IDictionary]$Secrets) {
    $machinePath = @(Get-MachinePath)
    for ($i = 0; $i -lt $systemPathDirs.Count; $i++) {
        if ($machinePath.Count -le $i -or $machinePath[$i] -ne $systemPathDirs[$i]) { return $false }
        if (@($machinePath | Where-Object { $_ -eq $systemPathDirs[$i] }).Count -ne 1) { return $false }
    }
    foreach ($name in $machineVars.Keys) {
        if ([Environment]::GetEnvironmentVariable($name, 'Machine') -ne $machineVars[$name]) { return $false }
    }
    foreach ($name in $Secrets.Keys) {
        if ([Environment]::GetEnvironmentVariable($name, 'Machine') -ne $Secrets[$name]) { return $false }
    }
    return $true
}
function Set-MachineSettings([System.Collections.IDictionary]$Secrets) {
    $previousHome = [Environment]::GetEnvironmentVariable('KILO_KIT_HOME', 'Machine')
    $envKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($envKeyPath, $true)
    try {
        $remove = $systemPathDirs + @(if ($previousHome) { & $pathDirs $previousHome })
        $kept = @(([string]$envKey.GetValue('Path', '', 'DoNotExpandEnvironmentNames')).Split(';') |
            Where-Object { $_ -and $remove -notcontains $_.TrimEnd('\') })
        # The bundled kilo, rg and fd must take precedence over other copies on PATH.
        $envKey.SetValue('Path', (($systemPathDirs + $kept) -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString)
    } finally { $envKey.Close() }
    # Setting variables through .NET broadcasts the change so newly opened terminals see the new values.
    foreach ($name in $machineVars.Keys) { [Environment]::SetEnvironmentVariable($name, $machineVars[$name], 'Machine') }
    foreach ($name in $Secrets.Keys) { [Environment]::SetEnvironmentVariable($name, $Secrets[$name], 'Machine') }
}
function Protect-Secrets([System.Collections.IDictionary]$Secrets) {
    # The elevated child may run as another administrator and gets a fresh environment, so secrets travel as an
    # argument. DPAPI keeps plain text out of process-creation logs.
    Add-Type -AssemblyName System.Security
    $plain = [Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject $Secrets -Compress))
    [Convert]::ToBase64String([Security.Cryptography.ProtectedData]::Protect($plain, $null, 'LocalMachine'))
}
function Unprotect-Secrets([string]$Blob) {
    $secrets = [ordered]@{}
    if (-not $Blob) { return $secrets }
    Add-Type -AssemblyName System.Security
    $plain = [Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($Blob), $null, 'LocalMachine')
    $parsed = [Text.Encoding]::UTF8.GetString($plain) | ConvertFrom-Json
    foreach ($property in $parsed.PSObject.Properties) { $secrets[$property.Name] = [string]$property.Value }
    return $secrets
}
function Test-Administrator {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if ($SystemOnly) {
    if (-not (Test-Administrator)) { throw 'Administrator rights are required to update system environment variables.' }
    Set-MachineSettings (Unprotect-Secrets $SecretBlob)
    return
}

$interactive = -not $NonInteractive -and [Environment]::UserInteractive -and -not [Console]::IsInputRedirected
function Read-Json([string]$Path) {
    try { return [IO.File]::ReadAllText($Path, $utf8) | ConvertFrom-Json }
    catch { throw "Invalid JSON in ${Path}: $($_.Exception.Message)" }
}
function Write-Text([string]$Path, [string]$Text) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    [IO.File]::WriteAllText($Path, $Text, $utf8)
}
function Install-File([string]$Path, [string]$Text) {
    # Keep one backup of a file that someone else wrote or that an older setup generated.
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        if ([IO.File]::ReadAllText($Path, $utf8) -ceq $Text) { return }
        Copy-Item -LiteralPath $Path -Destination "$Path.bak" -Force
        Write-Host "Backed up $Path -> $Path.bak"
    }
    Write-Text $Path $Text
}
function Read-Secret([string]$Prompt) {
    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}
function Get-SavedValue([string]$Name) {
    # Machine first: that is what new terminals get. The process value covers keys set some other way.
    $value = [Environment]::GetEnvironmentVariable($Name, 'Machine')
    if (-not $value) { $value = [Environment]::GetEnvironmentVariable($Name, 'Process') }
    return $value
}
function Invoke-Native([string]$File, [string[]]$Arguments) {
    # Windows PowerShell 5.1 turns native stderr into terminating errors under 'Stop'; collect it as text instead.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = @(& $File @Arguments 2>&1 | ForEach-Object { "$_" })
        return [pscustomobject]@{ Code = $LASTEXITCODE; Text = ($output -join "`n") }
    } finally { $ErrorActionPreference = $previous }
}
function Get-ContextWindow($Item) {
    # vLLM: max_model_len, LM Studio/OpenRouter style: context_length/max_context_length, llama.cpp: meta.n_ctx_train.
    foreach ($name in @('max_model_len', 'context_length', 'context_window', 'max_context_length', 'max_input_tokens')) {
        $value = $Item.$name -as [long]
        if ($value -gt 0) { return $value }
    }
    if ($Item.meta) {
        $value = $Item.meta.n_ctx_train -as [long]
        if ($value -gt 0) { return $value }
    }
    return $null
}
function Get-ApiModels([string]$Url, [string]$Key) {
    $headers = @{}
    if ($Key) { $headers['Authorization'] = "Bearer $Key" }
    try {
        $response = Invoke-RestMethod -Uri ($Url + '/models') -Headers $headers -Method Get -TimeoutSec 30 -UseBasicParsing
    } catch {
        $status = $null
        if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
        if ($status -eq 401 -or $status -eq 403) { throw "The model API rejected the API key (HTTP $status): $Url/models" }
        throw "Could not list models from $Url/models ($($_.Exception.Message))"
    }
    if ($response -is [string]) { $response = $response | ConvertFrom-Json }
    $items = @($response.data | Where-Object { $_ -and $_.id })
    if ($items.Count -eq 0) { throw "The model API returned no models: $Url/models" }
    foreach ($item in $items) { [pscustomobject]@{ id = [string]$item.id; contextWindow = (Get-ContextWindow $item) } }
}

# 1. Provider registration: config\models.json holds the API address, the key's variable name and the models found.
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$modelsPath = Join-Path $configDir 'models.json'
$registry = if (Test-Path -LiteralPath $modelsPath -PathType Leaf) { Read-Json $modelsPath } else { Read-Json (Join-Path $configDir 'models.example.json') }
if (-not $registry.provider) { throw "config\models.json has no provider. Copy config\models.example.json and run setup again." }
$provider = $registry.provider
$providerId = if ($provider.id) { [string]$provider.id } else { 'corp' }
$providerName = if ($provider.name) { [string]$provider.name } else { $providerId }
$keyEnv = if ($provider.apiKeyEnv) { [string]$provider.apiKeyEnv } else { 'CORP_LLM_API_KEY' }
if ($providerId -notmatch '^[a-z0-9_-]+$') { throw "provider.id must use lowercase letters, digits, '-' or '_': $providerId" }
if ($keyEnv -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw "provider.apiKeyEnv is not a valid variable name: $keyEnv" }
$url = if ($BaseUrl) { $BaseUrl } else { [string]$provider.baseUrl }
if (-not $BaseUrl -and ($Reconfigure -or -not $url -or $url -match '[<>]')) {
    if (-not $interactive) { throw 'Set provider.baseUrl in config\models.json or pass -BaseUrl, then run setup again.' }
    $url = Read-Host -Prompt 'Internal model API base URL (for example http://10.0.0.1:8000/v1)'
}
$url = $url.Trim().TrimEnd('/')
if ($url -notmatch '^https?://[^\s<>]+$') { throw "Not an http(s) URL: $url" }

# Secrets set during this run; unchanged values stay as they are on the machine.
$secrets = [ordered]@{}
$key = Get-SavedValue $keyEnv
if ($PSBoundParameters.ContainsKey('ApiKey')) {
    $key = $ApiKey
    if ($ApiKey) { $secrets[$keyEnv] = $ApiKey }
} elseif ($interactive -and ($Reconfigure -or -not $key)) {
    $entered = Read-Secret "API key for $url (hidden; Enter keeps the current value or uses no key)"
    if ($entered) { $key = $entered; $secrets[$keyEnv] = $entered }
}
foreach ($pair in @(@('REDISCLI_AUTH', $RedisPassword, 'RedisPassword', 'Build center Redis password (hidden; Enter to skip)', $true),
                    @('HSC_REDIS_USERNAME', $RedisUsername, 'RedisUsername', 'Build center Redis ACL user name (Enter to skip)', $false))) {
    $name, $value, $parameter, $prompt, $hidden = $pair
    if ($PSBoundParameters.ContainsKey($parameter)) {
        if ($value) { $secrets[$name] = $value }
    } elseif ($interactive -and ($Reconfigure -or -not (Test-Path -LiteralPath $modelsPath)) -and -not (Get-SavedValue $name)) {
        $value = if ($hidden) { Read-Secret $prompt } else { Read-Host -Prompt $prompt }
        if ($value) { $secrets[$name] = $value }
    }
}

# 2. Model discovery. The provider only needs an address and key; the model list comes from the API itself.
$known = @{}
foreach ($entry in @($registry.models | Where-Object { $_ -and $_.id })) { $known[[string]$entry.id] = $entry }
$found = $null
try {
    $found = @(Get-ApiModels $url $key)
} catch {
    $firstError = $_.Exception.Message
    if ($url -notmatch '/v1$') {
        try { $found = @(Get-ApiModels "$url/v1" $key); $url = "$url/v1" } catch { }
    }
    if (-not $found) {
        if ($known.Count -eq 0) { throw "$firstError. Check the address, API key and network, then run setup again." }
        Write-Warning "$firstError. Using the $($known.Count) model(s) already listed in config\models.json."
    }
}
$models = New-Object System.Collections.ArrayList
if ($found) {
    foreach ($item in $found) {
        $saved = $known[$item.id]
        # Values written by hand in models.json win over what the API reports.
        $context = if ($saved -and ($saved.contextWindow -as [long]) -gt 0) { [long]$saved.contextWindow } elseif ($item.contextWindow) { [long]$item.contextWindow } else { $null }
        $output = if ($saved -and ($saved.maxTokens -as [long]) -gt 0) { [long]$saved.maxTokens } else { $null }
        $name = if ($saved -and $saved.name) { [string]$saved.name } else { $item.id }
        [void]$models.Add([pscustomobject]@{ id = $item.id; name = $name; contextWindow = $context; maxTokens = $output })
    }
} else {
    foreach ($entry in $known.Values) {
        [void]$models.Add([pscustomobject]@{ id = [string]$entry.id; name = $(if ($entry.name) { [string]$entry.name } else { [string]$entry.id })
            contextWindow = ($entry.contextWindow -as [long]); maxTokens = ($entry.maxTokens -as [long]) })
    }
}
foreach ($entry in $models) {
    if (-not $entry.contextWindow) {
        $entry.contextWindow = [long]131072
        Write-Warning "The API does not report a context window for $($entry.id); assuming 131072 tokens. Set contextWindow in config\models.json if it differs."
    }
    if (-not $entry.maxTokens) { $entry.maxTokens = [long][Math]::Min(8192, [Math]::Max(1024, [Math]::Floor($entry.contextWindow / 4))) }
}
$ids = @($models | ForEach-Object { $_.id })
$chat = @($ids | Where-Object { $_ -notmatch '(?i)embed|rerank|whisper|tts|bge' })
if (-not $chat) { $chat = $ids }
if ($Model) {
    if ($ids -notcontains $Model) { throw "Model '$Model' is not offered by $url. Available: $($ids -join ', ')" }
    $default = $Model
} elseif (-not $Reconfigure -and $registry.default -and $ids -contains [string]$registry.default) {
    $default = [string]$registry.default
} elseif ($interactive -and $chat.Count -gt 1) {
    Write-Host 'Models offered by the API:'
    for ($i = 0; $i -lt $chat.Count; $i++) { Write-Host ("  [{0}] {1}" -f ($i + 1), $chat[$i]) }
    $choice = (Read-Host -Prompt 'Default model number (Enter = 1)').Trim()
    $index = if ($choice) { ($choice -as [int]) - 1 } else { 0 }
    if ($index -lt 0 -or $index -ge $chat.Count) { throw "No model number $choice." }
    $default = $chat[$index]
} else {
    $default = $chat[0]
}
$completed = [ordered]@{
    provider = [ordered]@{ id = $providerId; name = $providerName; baseUrl = $url; apiKeyEnv = $keyEnv }
    default  = $default
    models   = @($models | ForEach-Object { [ordered]@{ id = $_.id; name = $_.name; contextWindow = $_.contextWindow; maxTokens = $_.maxTokens } })
}
Install-File $modelsPath ((ConvertTo-Json -InputObject $completed -Depth 8) + "`n")
Write-Host "Provider $providerId ($url): $($ids.Count) model(s), default $default"

# 3. Kilo config for the current user, at Kilo's standard global location (%USERPROFILE%\.config\kilo).
# kilo.json is generated here on every run; kilo.jsonc is the user's own file and is read after it.
$userHome = [Environment]::GetFolderPath('UserProfile')
$kiloConfigDir = Join-Path $(if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { Join-Path $userHome '.config' }) 'kilo'
$kiloCacheBin = Join-Path $(if ($env:XDG_CACHE_HOME) { $env:XDG_CACHE_HOME } else { Join-Path $userHome '.cache' }) 'kilo\bin'
$template = Read-Json (Join-Path $configDir 'kilo.template.json')
$kiloConfig = [ordered]@{}
foreach ($property in $template.PSObject.Properties) { $kiloConfig[$property.Name] = $property.Value }
foreach ($server in $template.mcp.PSObject.Properties) {
    # Absolute paths: MCP servers start in the user's project folder and must not depend on PATH.
    $server.Value.command = @($server.Value.command | ForEach-Object { ([string]$_).Replace('{bundle}', $BundleRoot) })
}
$kiloModels = [ordered]@{}
foreach ($entry in $models) {
    $kiloModels[$entry.id] = [ordered]@{ name = $entry.name; tool_call = $true; limit = [ordered]@{ context = $entry.contextWindow; output = $entry.maxTokens } }
}
$kiloConfig['enabled_providers'] = @($providerId)
$kiloConfig['model'] = "$providerId/$default"
$kiloConfig['small_model'] = "$providerId/$default"
$kiloConfig['provider'] = [ordered]@{
    $providerId = [ordered]@{
        npm     = '@ai-sdk/openai-compatible'
        name    = $providerName
        env     = @($keyEnv)
        options = [ordered]@{ baseURL = $url }
        models  = $kiloModels
    }
}
Install-File (Join-Path $kiloConfigDir 'kilo.json') ((ConvertTo-Json -InputObject $kiloConfig -Depth 16) + "`n")
Install-File (Join-Path $kiloConfigDir 'AGENTS.md') ([IO.File]::ReadAllText((Join-Path $configDir 'AGENTS.md'), $utf8))
$userConfig = Join-Path $kiloConfigDir 'kilo.jsonc'
if (-not (Test-Path -LiteralPath $userConfig)) {
    Write-Text $userConfig ("// Personal Kilo settings. kilo-kit setup.ps1 never overwrites this file.`n" +
        "// Kilo reads it after kilo.json (generated by setup.ps1), so values here win.`n" +
        "{`n  `"`$schema`": `"https://app.kilo.ai/config.json`"`n}`n")
}
foreach ($name in @('kilo.jsonc', 'opencode.json', 'opencode.jsonc')) {
    $file = Join-Path $kiloConfigDir $name
    if ((Test-Path -LiteralPath $file) -and ([IO.File]::ReadAllText($file, $utf8) -match '"(model|provider|enabled_providers|mcp)"')) {
        Write-Warning "$file sets model, provider or MCP settings that override the ones setup.ps1 installed."
    }
}
# On Windows kilo ignores rg on PATH and downloads ripgrep into its cache when missing; the bundle provides it instead.
$rgTarget = Join-Path $kiloCacheBin 'rg.exe'
$rgSource = Join-Path $BundleRoot 'bin\rg.exe'
if (-not (Test-Path -LiteralPath $rgTarget) -or (Get-FileHash -LiteralPath $rgTarget).Hash -ne (Get-FileHash -LiteralPath $rgSource).Hash) {
    New-Item -ItemType Directory -Force -Path $kiloCacheBin | Out-Null
    Copy-Item -LiteralPath $rgSource -Destination $rgTarget -Force
}

# 4. Build center: empty local mappings on first run; never overwrite internal data on reruns.
foreach ($file in @('server_IP_mappings.json', 'owners.json')) {
    $mapping = Join-Path $configDir (Join-Path 'redis' $file)
    if (-not (Test-Path -LiteralPath $mapping)) { Write-Text $mapping '{}' }
}
# The MCP server runs on the bundled Python only; fail here rather than inside kilo.
$probe = Invoke-Native $python @('-I', '-X', 'utf8', '-B', '-c', "import main, redis, mcp; print('MCP_RUNTIME_OK')")
if ($probe.Code -or $probe.Text -notmatch 'MCP_RUNTIME_OK') { throw "Bundled MCP runtime check failed:`n$($probe.Text)" }

# 5. Machine PATH and variables. Elevate only for this step so per-user files above stay in the caller's profile.
if (-not (Test-SystemReady $secrets)) {
    if (Test-Administrator) {
        Set-MachineSettings $secrets
    } else {
        Write-Host 'Requesting administrator rights to update system environment variables...'
        $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-SystemOnly')
        if ($secrets.Count) { $arguments += @('-SecretBlob', (Protect-Secrets $secrets)) }
        try {
            Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Verb RunAs -Wait -ArgumentList $arguments
        } catch { throw "Administrator approval was not given; system environment variables were not updated. ($($_.Exception.Message))" }
    }
    if (-not (Test-SystemReady $secrets)) { throw 'System environment variables were not updated (administrator rights required).' }
}
# User variables override machine variables in new terminals; remove stale copies in the caller's own account.
foreach ($name in @($machineVars.Keys) + @($secrets.Keys)) {
    if ($null -ne [Environment]::GetEnvironmentVariable($name, 'User')) {
        [Environment]::SetEnvironmentVariable($name, $null, 'User')
        if ($null -ne [Environment]::GetEnvironmentVariable($name, 'User')) { throw "Could not remove conflicting user environment variable: $name" }
        Write-Host "Removed user variable that overrode the system setting: $name"
    }
}
foreach ($name in $machineVars.Keys) { [Environment]::SetEnvironmentVariable($name, $machineVars[$name], 'Process') }
foreach ($name in $secrets.Keys) { [Environment]::SetEnvironmentVariable($name, $secrets[$name], 'Process') }
$started = Invoke-Native $kiloExe @('--version')
$version = [regex]::Match($started.Text, '(?m)^\d+\.\d+\.\d+\S*').Value
if ($started.Code -or -not $version) { throw "kilo.exe did not start: $kiloExe`n$($started.Text)" }

Write-Host "Kilo $version, default model $providerId/$default"
Write-Host "Kilo settings: $kiloConfigDir (kilo.json is regenerated by setup; put your own changes in kilo.jsonc)"
Write-Host "System PATH: $($systemPathDirs -join ', ')"
Write-Host "Setup complete. Fully close your terminal application, reopen it, and run 'kilo' in any folder."
