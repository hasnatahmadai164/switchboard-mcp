<#
.SYNOPSIS
    Calls a Switchboard MCP tool via Inspector's CLI, without the
    quoting/line-continuation problems of hand-typing the full npx
    command every time.

    Array splatting (npx @argList below) passes each argument as its own
    real element to the process -- there's no string re-parsing for
    PowerShell to get wrong, unlike a long backtick-continued command
    pasted from a chat window, which is exactly what kept breaking.

.EXAMPLE
    $env:SWITCHBOARD_TOKEN = "eyJ..."
    .\scripts\call-tool.ps1 -ToolName list_sheets -ToolArgs @{ spreadsheet_id = "1NtZPJn..." }

.EXAMPLE
    .\scripts\call-tool.ps1 -ToolName list_tables
#>
param(
    [Parameter(Mandatory = $true)][string]$ToolName,
    [hashtable]$ToolArgs = @{}
)

$token = $env:SWITCHBOARD_TOKEN
if (-not $token) {
    Write-Error 'Set $env:SWITCHBOARD_TOKEN first, e.g. $env:SWITCHBOARD_TOKEN = "eyJ..."'
    exit 1
}

$argList = @(
    "@modelcontextprotocol/inspector"
    "--cli"
    "http://localhost:8000/mcp"
    "--transport"
    "http"
    "--header"
    "Authorization: Bearer $token"
    "--method"
    "tools/call"
    "--tool-name"
    $ToolName
)

foreach ($key in $ToolArgs.Keys) {
    $argList += "--tool-arg"
    $argList += "$key=$($ToolArgs[$key])"
}

npx @argList
