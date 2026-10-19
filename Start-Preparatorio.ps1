$ErrorActionPreference = 'Stop'
$taskFrontend = Join-Path $PSScriptRoot 'frontend'
$taskNodeCommand = Get-Command node -ErrorAction SilentlyContinue
$taskNodePath = if ($taskNodeCommand) { $taskNodeCommand.Source } else {
    Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
}
if (-not (Test-Path -LiteralPath $taskNodePath)) { throw 'Node.js não encontrado. Instale Node.js para executar o projeto.' }
$taskVitePath = Join-Path $taskFrontend 'node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $taskVitePath)) { throw 'Dependências ausentes. Execute npm install na pasta frontend.' }
$taskServerPath = Join-Path $PSScriptRoot 'multiplayer\server.js'
$taskServerProcess = $null

function Get-PrepListener {
    param([int]$Port, [string]$ScriptPath, [string]$Label)
    $taskListeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if (-not $taskListeners.Count) { return $null }
    $taskProcessIds = @($taskListeners | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($taskProcessIds.Count -ne 1) { throw "A porta $Port tem serviços conflitantes. O $Label não foi iniciado." }
    $taskOwner = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $taskProcessIds[0])
    $taskScriptArgument = '(?i)(?:^|[\s"])' + [regex]::Escape($ScriptPath) + '(?=$|[\s"])'
    if ($taskOwner.Name -ne 'node.exe' -or $taskOwner.CommandLine -notmatch $taskScriptArgument) {
        throw "A porta $Port pertence a outro programa. O $Label não foi iniciado; nenhum processo foi encerrado."
    }
    return $taskOwner
}

function Test-PrepSharedReady {
    try {
        $taskHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:5180/health' -TimeoutSec 1
        return $taskHealth.ok -and $taskHealth.mode -eq 'local-demo' -and 'cyber' -in $taskHealth.rooms
    } catch { return $false }
}

# Check both ports before starting anything. A familiar page title alone is not
# enough: the listening Node process must run this project's exact script.
$taskFrontendOwner = Get-PrepListener -Port 5173 -ScriptPath $taskVitePath -Label 'jogo'
$taskSharedOwner = Get-PrepListener -Port 5180 -ScriptPath $taskServerPath -Label 'servidor local'
if ($taskFrontendOwner) {
    try {
        $taskPage = Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 5
        if ($taskPage.StatusCode -ne 200 -or $taskPage.Content -notmatch 'PREPARAT' -or $taskPage.Content -notmatch '/src/main\.jsx') {
            throw 'A resposta não corresponde ao frontend deste projeto.'
        }
    } catch { throw "O frontend da porta 5173 não está pronto. Nenhuma segunda instância foi iniciada. $($_.Exception.Message)" }
}
$taskSharedReady = if ($taskSharedOwner) { Test-PrepSharedReady } else { $false }
if ($taskSharedOwner -and -not $taskSharedReady) {
    throw 'O servidor deste projeto ocupa a porta 5180, mas não respondeu corretamente. Nenhuma segunda instância foi iniciada.'
}
if (-not $taskSharedOwner) {
    $taskServerProcess = Start-Process -FilePath $taskNodePath -ArgumentList @('"' + $taskServerPath + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru
    for ($taskAttempt = 0; $taskAttempt -lt 30 -and -not $taskSharedReady; $taskAttempt++) {
        Start-Sleep -Milliseconds 100
        $taskSharedReady = Test-PrepSharedReady
        if ($taskServerProcess.HasExited) { break }
    }
    if (-not $taskSharedReady) { throw 'Não foi possível iniciar a sala compartilhada local na porta 5180.' }
}
Write-Host 'Sala compartilhada local pronta. Abra duas abas para testar dois jogadores.'
if ($taskFrontendOwner) {
    # A backend just started here must remain available for the already-running
    # frontend. Do not enter the foreground-launch cleanup branch below.
    Write-Host 'Jogo já aberto em http://127.0.0.1:5173/ — serviços existentes reutilizados.'
    return
}
Write-Host 'Iniciando o jogo em http://127.0.0.1:5173/.'
Push-Location -LiteralPath $taskFrontend
try { & $taskNodePath $taskVitePath --host 127.0.0.1 --port 5173 --strictPort } finally {
    Pop-Location
    if ($taskServerProcess -and -not $taskServerProcess.HasExited) { Stop-Process -Id $taskServerProcess.Id }
}
