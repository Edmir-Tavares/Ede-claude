# Sets up and starts OpenHiggsfield (https://github.com/wide-trace/open-higgsfield) on Windows.
# Run in PowerShell:  powershell -ExecutionPolicy Bypass -File .\setup-open-higgsfield.ps1
# Safe to run again: it skips anything already done and never overwrites .env.local.

$ErrorActionPreference = "Stop"
$ProjectDir = Join-Path $HOME "open-higgsfield"

function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path", "User")
}

function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# 1. Git
if (-not (Has git)) {
  Write-Host "Installing Git..." -ForegroundColor Cyan
  winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
  Refresh-Path
}

# 2. Node.js 22 LTS (Next.js 16 needs Node 20.9 or newer)
$needNode = $true
if (Has node) {
  $major = [int]((node -v).TrimStart("v").Split(".")[0])
  if ($major -ge 22) { $needNode = $false }
}
if ($needNode) {
  Write-Host "Installing Node.js 22 LTS..." -ForegroundColor Cyan
  winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
  Refresh-Path
}

# 3. pnpm 10 (the project's pnpm-workspace.yaml uses pnpm 10 settings)
if (-not (Has pnpm) -or -not ((pnpm -v) -like "10.*")) {
  Write-Host "Installing pnpm 10..." -ForegroundColor Cyan
  npm install -g pnpm@10
  Refresh-Path
}

Write-Host ("git " + (git --version) + " | node " + (node -v) + " | pnpm " + (pnpm -v)) -ForegroundColor Green

# 4. Clone
if (-not (Test-Path (Join-Path $ProjectDir "package.json"))) {
  git clone https://github.com/wide-trace/open-higgsfield.git $ProjectDir
}
Set-Location $ProjectDir

# 5. Dependencies
pnpm install --frozen-lockfile

# 6. Local config. HF_API_BASE_URL is Higgsfield's documented API address.
#    The upload token is left empty for you to fill in yourself.
$envFile = Join-Path $ProjectDir ".env.local"
if (-not (Test-Path $envFile)) {
  @(
    "HF_API_BASE_URL=https://api.higgsfield.ai",
    "OPEN_HIGGSFIELD_READ_WRITE_TOKEN="
  ) | Set-Content -Path $envFile -Encoding ascii
  Write-Host "Created $envFile" -ForegroundColor Green
}

# 7. Start and open the browser once the server answers
Write-Host "Starting http://localhost:3000  (press Ctrl+C in this window to stop)" -ForegroundColor Cyan
Start-Job -ScriptBlock {
  for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest "http://localhost:3000" -UseBasicParsing -TimeoutSec 5 | Out-Null; break }
    catch { Start-Sleep -Seconds 2 }
  }
  Start-Process "http://localhost:3000"
} | Out-Null
pnpm dev
