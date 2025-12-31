# Refresh PATH and build
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Set-Location src-tauri
cargo check 2>&1 | Out-File -FilePath "../build-log.txt"
Get-Content ../build-log.txt -Tail 50
