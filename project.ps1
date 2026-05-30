param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppFile = Join-Path $ProjectRoot "app.py"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$PidFile = Join-Path $ProjectRoot ".streamlit.pid"
$LogDir = Join-Path $ProjectRoot ".logs"
$StdoutLog = Join-Path $LogDir "streamlit.out.log"
$StderrLog = Join-Path $LogDir "streamlit.err.log"
$Port = 8501
$Url = "http://localhost:$Port"

function Write-Step($Message) {
    Write-Host "[CMIT] $Message"
}

function Get-ListeningProcessIds {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return @()
    }

    return @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Get-SavedProcess {
    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $savedPid = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $savedPid) {
        return $null
    }

    return Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
}

function Ensure-Python {
    if (Test-Path $VenvPython) {
        return
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python is not available in PATH. Please install Python, then run this script again."
    }

    Write-Step "Creating virtual environment..."
    Push-Location $ProjectRoot
    try {
        & python -m venv .venv
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Path $VenvPython)) {
        throw "Could not create .venv. Please check your Python installation."
    }
}

function Ensure-Dependencies {
    if (-not (Test-Path $RequirementsFile)) {
        throw "requirements.txt not found."
    }

    $stampFile = Join-Path $VenvDir ".requirements.stamp"
    $shouldInstall = -not (Test-Path $stampFile)

    if (-not $shouldInstall) {
        $requirementsTime = (Get-Item $RequirementsFile).LastWriteTimeUtc
        $stampTime = (Get-Item $stampFile).LastWriteTimeUtc
        $shouldInstall = $requirementsTime -gt $stampTime
    }

    if ($shouldInstall) {
        Write-Step "Installing Python dependencies..."
        & $VenvPython -m pip install --upgrade pip
        & $VenvPython -m pip install -r $RequirementsFile
        Set-Content -Path $stampFile -Value (Get-Date).ToString("s")
    }
}

function Start-App {
    if (-not (Test-Path $AppFile)) {
        throw "app.py not found."
    }

    $running = Get-SavedProcess
    if ($running) {
        Write-Step "Project is already running at $Url (PID $($running.Id))."
        Start-Process $Url
        return
    }

    $listeningPids = Get-ListeningProcessIds
    if ($listeningPids.Count -gt 0) {
        Write-Step "Port $Port is already in use by PID(s): $($listeningPids -join ', ')."
        Write-Step "If this is the old project process, run: .\project.ps1 stop"
        return
    }

    Ensure-Python
    Ensure-Dependencies

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    Write-Step "Starting Streamlit on $Url..."
    $arguments = @(
        "-m", "streamlit", "run", $AppFile,
        "--server.port", "$Port",
        "--server.headless", "true"
    )

    $process = Start-Process `
        -FilePath $VenvPython `
        -ArgumentList $arguments `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path $PidFile -Value $process.Id
    Start-Sleep -Seconds 3

    if ($process.HasExited) {
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        Write-Step "Streamlit exited while starting. Check logs:"
        Write-Host $StdoutLog
        Write-Host $StderrLog
        exit 1
    }

    $code = Get-Command code -ErrorAction SilentlyContinue
    if ($code) {
        Write-Step "Opening project in VSCode..."
        Start-Process -FilePath $code.Source -ArgumentList "`"$ProjectRoot`""
    }

    Write-Step "Opening browser..."
    Start-Process $Url
    Write-Step "Project is ready: $Url"
}

function Stop-App {
    $stopped = $false
    $running = Get-SavedProcess

    if ($running) {
        Write-Step "Stopping Streamlit PID $($running.Id)..."
        Stop-Process -Id $running.Id -Force
        $stopped = $true
    }

    $listeningPids = Get-ListeningProcessIds
    foreach ($processId in $listeningPids) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Step "Stopping process on port ${Port}: PID $processId..."
            Stop-Process -Id $processId -Force
            $stopped = $true
        }
    }

    Remove-Item $PidFile -ErrorAction SilentlyContinue

    if ($stopped) {
        Write-Step "Project stopped."
    }
    else {
        Write-Step "Project is not running."
    }
}

function Show-Status {
    $running = Get-SavedProcess
    $listeningPids = Get-ListeningProcessIds

    if ($running) {
        Write-Step "Project is running at $Url (PID $($running.Id))."
        return
    }

    if ($listeningPids.Count -gt 0) {
        Write-Step "Port $Port is in use by PID(s): $($listeningPids -join ', ')."
        return
    }

    Write-Step "Project is not running."
}

switch ($Action) {
    "start" {
        Start-App
    }
    "stop" {
        Stop-App
    }
    "restart" {
        Stop-App
        Start-Sleep -Seconds 1
        Start-App
    }
    "status" {
        Show-Status
    }
}
