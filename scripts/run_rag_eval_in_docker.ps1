param(
  [string]$Container = "cerebro_mcp"
)

$ErrorActionPreference = "Stop"

Write-Host "Running Docker RAG scoped smoke checks on container: $Container"

function Get-JsonPayload {
  param([object]$RawText)
  if ($RawText -is [System.Array]) {
    $joined = ($RawText -join "`n")
  } else {
    $joined = [string]$RawText
  }
  $lines = $joined -split "(`r`n|`n|`r)"
  $start = -1
  for ($i = 0; $i -lt $lines.Length; $i++) {
    if ($lines[$i].TrimStart().StartsWith("{")) {
      $start = $i
      break
    }
  }
  if ($start -lt 0) {
    throw "No JSON payload found in command output."
  }
  return ($lines[$start..($lines.Length - 1)] -join "`n")
}

$ready = $false
for ($i = 0; $i -lt 20; $i++) {
  $state = docker inspect -f "{{.State.Running}}" $Container 2>$null
  if ($state -eq "true") {
    $ready = $true
    break
  }
  Start-Sleep -Milliseconds 500
}
if (-not $ready) {
  Write-Error "Container '$Container' is not running yet."
  exit 1
}

$ingest1 = docker exec $Container python -m cerebro_python rag-ingest --document-id alpha-dev --text "alpha dev architecture and coding standards" --project-id alpha --environment-id dev
$ingest2 = docker exec $Container python -m cerebro_python rag-ingest --document-id beta-dev --text "beta dev architecture and coding standards" --project-id beta --environment-id dev
$ingest3 = docker exec $Container python -m cerebro_python rag-ingest --document-id alpha-prod --text "alpha production rollback and release process" --project-id alpha --environment-id prod

$searchStrictRaw = docker exec $Container python -m cerebro_python rag-search --query "rollback release process" --top-k 5 --project-id alpha --environment-id dev
$searchExpandedRaw = docker exec $Container python -m cerebro_python rag-search --query "rollback release process" --top-k 5 --project-id alpha --environment-id dev --scope-mode custom --include-environment-id prod

$searchStrict = Get-JsonPayload -RawText $searchStrictRaw
$searchExpanded = Get-JsonPayload -RawText $searchExpandedRaw

$strictObj = $searchStrict | ConvertFrom-Json
$expandedObj = $searchExpanded | ConvertFrom-Json

$strictHasProd = $false
foreach ($item in $strictObj.results) {
  if ($item.metadata.environment_id -eq "prod") { $strictHasProd = $true }
}

$expandedHasProd = $false
foreach ($item in $expandedObj.results) {
  if ($item.metadata.environment_id -eq "prod") { $expandedHasProd = $true }
}

$ok = (-not $strictHasProd) -and $expandedHasProd

$payload = [ordered]@{
  status = if ($ok) { "success" } else { "failed" }
  strict_count = $strictObj.count
  expanded_count = $expandedObj.count
  strict_has_prod = $strictHasProd
  expanded_has_prod = $expandedHasProd
}

$payload | ConvertTo-Json -Depth 6

if (-not $ok) {
  exit 1
}
