@echo off
setlocal
rem Process-local: do not put npm offline mode in the machine environment.
set "npm_config_offline=true"
set "npm_config_audit=false"
set "npm_config_fund=false"
set "OPENCODE_KIT_HOME=%~dp0.."
rem Leave unrelated/partially initialized opencode.db untouched. Honor explicit user overrides.
if not defined OPENCODE_DB set "OPENCODE_DB=opencode-kit.db"
set "OPENCODE_DISABLE_AUTOUPDATE=1"
set "OPENCODE_DISABLE_MODELS_FETCH=1"
set "OPENCODE_DISABLE_DEFAULT_PLUGINS=true"
set "OPENCODE_DISABLE_LSP_DOWNLOAD=true"
rem Do not inherit an unrelated telemetry export endpoint.
set "OTEL_EXPORTER_OTLP_ENDPOINT="
set "OTEL_EXPORTER_OTLP_HEADERS="
"%~dp0opencode\opencode.exe" %*
exit /b %errorlevel%
