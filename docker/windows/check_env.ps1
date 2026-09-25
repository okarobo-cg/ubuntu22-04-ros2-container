<#
.SYNOPSIS
  Windows で diffbot_sim を動かすための環境をチェックする (うまく起動しないときに実行)。
.EXAMPLE
  .\check_env.ps1
#>
. (Join-Path $PSScriptRoot 'common.ps1')

$ng = 0

Write-Step 'Windows のバージョン'
$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
Write-Host "  $($os.Caption) (build $build)"
if ($build -ge 22000) {
    Write-Ok 'Windows 11: WSLg (GUI 表示) が使えます'
} elseif ($build -ge 19044) {
    Write-Warn2 'Windows 10: Microsoft Store 版の WSL (wsl --update) なら WSLg が使えます。ダメなら -Display vcxsrv'
} else {
    Write-Ng 'Windows が古すぎます (Windows 10 21H2 以降が必要)'; $ng++
}

Write-Step 'WSL'
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    $env:WSL_UTF8 = '1'   # wsl の出力を文字化けさせない
    $v = wsl --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $v) {
        $v | Select-Object -First 3 | ForEach-Object { Write-Host "  $_" }
        Write-Ok 'WSL が入っています'
    } else {
        Write-Warn2 'wsl --version が使えません。管理者 PowerShell で "wsl --update" を実行してください'
    }
} else {
    Write-Ng 'WSL が入っていません。管理者 PowerShell で "wsl --install" を実行して再起動してください'; $ng++
}

Write-Step 'Docker Desktop'
if (Test-DockerRunning) {
    $sv = docker version --format '{{.Server.Version}}' 2>$null
    $os2 = docker info --format '{{.OperatingSystem}}' 2>$null
    Write-Ok "Docker Engine $sv ($os2)"
    $ostype = docker info --format '{{.OSType}}' 2>$null
    if ($ostype -ne 'linux') {
        Write-Ng 'Windows コンテナモードになっています。タスクトレイの Docker アイコン → "Switch to Linux containers"'; $ng++
    }
} else {
    $ng++
}

Write-Step 'ディスクの空き容量 (イメージに約 4 GB 必要)'
$drive = (Get-Item $Script:ProjectRoot).PSDrive
$freeGB = [math]::Round($drive.Free / 1GB, 1)
if ($freeGB -ge 10) { Write-Ok "$($drive.Name): ドライブの空き $freeGB GB" }
else { Write-Warn2 "$($drive.Name): ドライブの空き $freeGB GB (少なめです)" }

Write-Step 'プロジェクトのフォルダ構成'
Write-Host "  プロジェクト: $Script:ProjectRoot"
foreach ($f in @('src\diffbot_sim\package.xml', 'src\robocon2027_field\package.xml', 'src\docker\Dockerfile', 'src\docker\entrypoint.sh')) {
    if (Test-Path (Join-Path $Script:ProjectRoot $f)) { Write-Ok $f } else { Write-Ng "$f がありません"; $ng++ }
}
# entrypoint.sh が CRLF になっているとコンテナが起動しない (Git の autocrlf が原因)
$ep = Join-Path $Script:DockerDir 'entrypoint.sh'
if (Test-Path $ep) {
    $bytes = [System.IO.File]::ReadAllBytes($ep)
    if ($bytes -contains 13) {
        Write-Warn2 'entrypoint.sh の改行が CRLF です (Dockerfile 側で自動変換するので通常は問題なし)'
    } else {
        Write-Ok 'entrypoint.sh の改行は LF'
    }
}

if ($ng -eq 0 -and (Test-ImageExists)) {
    Write-Step 'コンテナから見た WSLg / GPU'
    $out = docker run --rm -v /run/desktop/mnt/host/wslg:/mnt/wslg -v /dev:/hostdev --entrypoint bash $Script:ImageName -c 'ls /mnt/wslg/.X11-unix/X0 >/dev/null 2>&1 && echo WSLG_OK ; ls /hostdev/dxg >/dev/null 2>&1 && echo DXG_OK' 2>$null
    if ($out -match 'WSLG_OK') { Write-Ok 'WSLg の X11 ソケットが見えます (-Display wslg が使えます)' }
    else { Write-Warn2 'WSLg が見えません。WSL を更新 (wsl --update) するか、-Display vcxsrv を使ってください' }
    if ($out -match 'DXG_OK') { Write-Ok '/dev/dxg (WSL2 の GPU) が見えます (-Gpu を試せます)' }
    else { Write-Warn2 '/dev/dxg が見えません (-Gpu は使えません。CPU 描画で動作します)' }
} elseif ($ng -eq 0) {
    Write-Step 'イメージ'
    Write-Warn2 "イメージ $Script:ImageName がまだありません。start.bat を実行するとビルドされます (その後もう一度このチェックを実行すると WSLg/GPU も確認できます)"
}

Write-Step 'コンテナ'
if (Test-ContainerRunning) { Write-Ok "コンテナ $Script:Container は起動中" }
else { Write-Host "  コンテナ $Script:Container は起動していません" }

Write-Host ''
if ($ng -eq 0) { Write-Host '結果: 問題は見つかりませんでした' -ForegroundColor Green }
else { Write-Host "結果: $ng 件の問題があります (上の [NG] を確認)" -ForegroundColor Red; exit 1 }
