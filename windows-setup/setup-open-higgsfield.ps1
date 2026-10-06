# Sets up and starts OpenHiggsfield (https://github.com/wide-trace/open-higgsfield) on Windows.
# Run in PowerShell:  powershell -ExecutionPolicy Bypass -File .\setup-open-higgsfield.ps1
# Safe to run again: it skips anything already done and never overwrites .env.local.
# Keep price-and-upload.patch in the same folder as this script: it adds the
# price shown before Generate and uploads reference files to Higgsfield.

$ErrorActionPreference = "Stop"
$ProjectDir = Join-Path $HOME "open-higgsfield"
$Patch = Join-Path $PSScriptRoot "price-and-upload.patch"
# The upstream commit the patch was written and tested against.
$BaseCommit = "b16a0ef"

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

# 4. Clone. Line endings stay as committed so the patch applies byte for byte.
if (-not (Test-Path (Join-Path $ProjectDir "package.json"))) {
  git -c core.autocrlf=false clone https://github.com/wide-trace/open-higgsfield.git $ProjectDir
}
Set-Location $ProjectDir
git config core.autocrlf false

# 5. Price preview + Higgsfield uploads
if (-not (Test-Path $Patch)) { throw "price-and-upload.patch not found next to this script." }
# Windows PowerShell turns redirected git stderr into a stopping error, so
# relax that for the one check that is expected to fail on a fresh clone.
$ErrorActionPreference = "Continue"
git apply --reverse --check $Patch 2>$null
$alreadyApplied = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"
if ($alreadyApplied) {
  Write-Host "Price preview already installed." -ForegroundColor Green
} else {
  if (git status --porcelain --untracked-files=no) {
    throw "The project folder has local edits. Move them aside (git stash) and run this script again."
  }
  git checkout -q -B studio $BaseCommit
  # Rewrite the working files with the committed line endings (a clone made by
  # the previous version of this script may have converted them).
  git rm -r -q --cached .
  git reset -q --hard
  git apply $Patch
  if ($LASTEXITCODE -ne 0) { throw "Could not apply price-and-upload.patch." }
  Write-Host "Price preview installed." -ForegroundColor Green
}

# 6. Dependencies
pnpm install --frozen-lockfile

# 7. Local config. HF_API_BASE_URL is Higgsfield's documented API address.
#    Your API key is NOT stored here: you paste it into the app's "API key" box.
$envFile = Join-Path $ProjectDir ".env.local"
if (-not (Test-Path $envFile)) {
  @("HF_API_BASE_URL=https://api.higgsfield.ai") | Set-Content -Path $envFile -Encoding ascii
  Write-Host "Created $envFile" -ForegroundColor Green
}

# 8. Start and open the browser once the server answers
Write-Host "Starting http://localhost:3000  (press Ctrl+C in this window to stop)" -ForegroundColor Cyan
Start-Job -ScriptBlock {
  for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest "http://localhost:3000" -UseBasicParsing -TimeoutSec 5 | Out-Null; break }
    catch { Start-Sleep -Seconds 2 }
  }
  Start-Process "http://localhost:3000"
} | Out-Null
pnpm dev
