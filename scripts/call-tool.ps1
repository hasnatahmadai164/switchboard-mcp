<#
.SYNOPSIS
    Calls the Switchboard MCP server via Inspector's CLI -- tools, and
    now resources too -- without the quoting/line-continuation problems
    of hand-typing the full npx command every time.

    Array splatting (npx @argList below) passes each argument as its own
    real element to the process -- there's no string re-parsing for
    PowerShell to get wrong.

.EXAMPLE
    $env:SWITCHBOARD_TOKEN = "eyJ..."
    .\scripts\call-tool.ps1 -ToolName list_tables

.EXAMPLE
    .\scripts\call-tool.ps1 -ToolName list_sheets -ToolArgs @{ spreadsheet_id = "1NtZPJn..." }

.EXAMPLE
    .\scripts\call-tool.ps1 -Method resources/list

.EXAMPLE
    .\scripts\call-tool.ps1 -Method prompts/get -ToolName draft_follow_up_email -ToolArgs @{ recipient_name = "Priya"; topic = "the Q3 proposal" }
#>
param(
    [string]$Method = "tools/call",
    [string]$ToolName,
    [hashtable]$ToolArgs = @{},
    [string]$Uri
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
    $Method
)

# prompts/get uses --prompt-name/--prompt-arg; everything else
# (tools/call) uses --tool-name/--tool-arg -- same -ToolName/-ToolArgs
# parameters either way, so you don't have to remember which flag goes
# with which method.
if ($Method -like "prompts/*") {
    $nameFlag = "--prompt-name"
    $argFlag = "--prompt-arg"
} else {
    $nameFlag = "--tool-name"
    $argFlag = "--tool-arg"
}

if ($ToolName) {
    $argList += $nameFlag
    $argList += $ToolName
    foreach ($key in $ToolArgs.Keys) {
        $argList += $argFlag
        $argList += "$key=$($ToolArgs[$key])"
    }
}

if ($Uri) {
    $argList += "--uri"
    $argList += $Uri
}

npx @argList
