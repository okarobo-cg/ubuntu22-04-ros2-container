# =============================================================
#  diffbot_sim Windows スクリプト共通処理 (他の .ps1 から読み込んで使う)
# =============================================================

# 注意: Windows PowerShell 5.1 では 'Stop' にすると docker の標準エラー出力だけで例外になるので
#       'Continue' にして、外部コマンドの成否は $LASTEXITCODE で判定する
$ErrorActionPreference = 'Continue'

# パス
$Script:DockerDir   = Split-Path -Parent $PSScriptRoot                 # <プロジェクト>\src\docker
$Script:SrcDir      = Split-Path -Parent $Script:DockerDir             # <プロジェクト>\src
$Script:ProjectRoot = Split-Path -Parent $Script:SrcDir                # <プロジェクト>
$Script:ComposeFile = Join-Path $Script:DockerDir 'docker-compose.windows.yml'
$Script:GpuFile     = Join-Path $Script:DockerDir 'docker-compose.windows-gpu.yml'
$Script:ImageName   = 'diffbot_sim:humble'
$Script:Container   = 'ubuntu_22_04_ros2'

function Write-Step([string]$msg) {
    Write-Host ''
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Write-Ok([string]$msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg) { Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function Write-Ng([string]$msg)   { Write-Host "  [NG] $msg" -ForegroundColor Red }

# docker compose に渡す -f 引数
function Get-ComposeArgs([switch]$Gpu) {
    $a = @('compose', '-f', $Script:ComposeFile)
    if ($Gpu) { $a += @('-f', $Script:GpuFile) }
    return $a
}

# docker compose を実行 (失敗したら止める)
function Invoke-Compose([string[]]$ComposeArgs, [string[]]$Rest) {
    & docker @ComposeArgs @Rest
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($ComposeArgs + $Rest -join ' ') が失敗しました (exit code $LASTEXITCODE)"
    }
}

# Docker Desktop が起動しているか
function Test-DockerRunning {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Ng 'docker コマンドが見つかりません。Docker Desktop をインストールしてください。'
        Write-Host '       https://docs.docker.com/desktop/setup/install/windows-install/'
        return $false
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Ng 'Docker Desktop が起動していません。スタートメニューから Docker Desktop を起動し、'
        Write-Host '       画面左下が "Engine running" になってから再実行してください。'
        return $false
    }
    return $true
}

# イメージがあるか
function Test-ImageExists {
    docker image inspect $Script:ImageName *> $null
    return ($LASTEXITCODE -eq 0)
}

# コンテナが起動中か
function Test-ContainerRunning {
    $state = docker inspect -f '{{.State.Running}}' $Script:Container 2>$null
    return ($LASTEXITCODE -eq 0 -and $state -eq 'true')
}

# compose がマウントする空フォルダを作る (無いと Docker が勝手に作ってしまう)
function Initialize-ProjectDirs {
    foreach ($d in 'config', 'models', 'worlds') {
        $p = Join-Path $Script:ProjectRoot $d
        if (-not (Test-Path $p)) {
            New-Item -ItemType Directory -Path $p | Out-Null
            Write-Ok "フォルダを作成: $p"
        }
    }
}

# GUI の表示先 (compose ファイルの ${DIFFBOT_DISPLAY} に渡す)
function Set-DisplayEnv([string]$Display) {
    switch ($Display) {
        'wslg'   { $env:DIFFBOT_DISPLAY = ':0' }
        'vcxsrv' { $env:DIFFBOT_DISPLAY = 'host.docker.internal:0.0' }
    }
}
