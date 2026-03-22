---
title: "Zero to 33 Tools: Building the First MCP Server for ActiveCampaign"
published: false
description: "33 tools for the ActiveCampaign API, built with Python and the official MCP SDK. Contacts, deals, automations, tags, pipelines, campaigns, and more — directly from Claude, Cursor, or any MCP client."
tags: mcp, ai, python, activecampaign
cover_image: https://raw.githubusercontent.com/AlexlaGuardia/MCP-Activecampaign/main/cover.png
---

I searched GitHub, npm, PyPI, and every MCP registry I could find for an ActiveCampaign MCP server. Zero results. Not a bad one, not an incomplete one — nothing. For a platform with 185,000 paying customers and a full-featured API, that gap felt worth filling.

So I built it from scratch: 33 tools covering contacts, deals, automations, tags, pipelines, campaigns, custom fields, and webhooks.

## What It Does

[MCP](https://modelcontextprotocol.io/) lets AI assistants interact with external tools directly. With this server installed, you manage your CRM and marketing automation without leaving your AI assistant.

**Before (manual):**
1. Log into ActiveCampaign
2. Navigate to Contacts → search for a customer
3. Check their tags, deals, automation history
4. Switch to your AI tool
5. Describe what you found
6. Ask for analysis

**After (with mcp-activecampaign):**
> "Find all contacts tagged 'enterprise-lead' and show me their deal pipeline status. Which ones haven't been contacted in 30 days?"

Claude calls `list_contacts` with a tag filter, then `list_deals` for each, and gives you an actionable priority list — all in one shot.

## 33 Tools, Full CRM Coverage

- **Contacts** (7): List, get, create, update, delete, search, manage tags
- **Deals** (5): List, get, create, update, delete with pipeline/stage support
- **Tags** (4): List, create, add to contact, remove from contact
- **Lists** (2): List all, get details with subscriber counts
- **Automations** (3): List, get details, add contacts to automations
- **Pipelines** (2): List pipelines, list stages within pipelines
- **Custom Fields** (3): List fields, get values, set values per contact
- **Campaigns** (2): List campaigns with stats, get full campaign details
- **Accounts** (2): List and get company/organization records
- **Webhooks** (3): List, create, delete for real-time event handling

## Technical Decisions Worth Sharing

### Client-Side Rate Limiting

ActiveCampaign enforces 5 requests per second per account. Hit the limit and you get 429s that can cascade. Instead of reacting to failures, the client prevents them:

```python
MAX_RPS = 5
MIN_INTERVAL = 1.0 / MAX_RPS  # 0.2s between requests

async def _throttle(self) -> None:
    """Enforce 5 req/s rate limit."""
    async with self._lock:
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self.MIN_INTERVAL:
            await asyncio.sleep(self.MIN_INTERVAL - elapsed)
        self._last_request = time.monotonic()
```

An asyncio lock ensures thread safety, and `time.monotonic()` avoids clock-drift edge cases. If a 429 still slips through (burst from another client), there's a fallback that respects the `Retry-After` header:

```python
if resp.status_code == 429:
    retry_after = float(resp.headers.get("Retry-After", "1"))
    await asyncio.sleep(retry_after)
    return await self._request(method, path, **kwargs)
```

Belt and suspenders. The AI never sees rate limit errors.

### The "Deal Groups" Translation

ActiveCampaign calls pipelines "deal groups" internally. The API endpoint is `/dealGroups`, stages are filtered by `d_groupid`, and creating a deal requires a `group` field — not `pipeline`. This naming inconsistency trips up every integration:

```python
@mcp.tool()
async def list_pipelines(limit: int = 20, offset: int = 0) -> str:
    """List deal pipelines (called 'deal groups' in AC API)."""
    data = await ac.get("/dealGroups", ...)
    for p in data.get("dealGroups", []):
        pipelines.append({
            "id": p["id"],
            "title": p.get("title", ""),
            ...
        })
```

The tools use the word "pipeline" (what users expect) while the client sends "dealGroup" (what the API expects). The AI works with natural language; the translation happens silently.

### URL Normalization with API Path

ActiveCampaign API URLs look like `https://youraccountname.api-us1.com/api/3/contacts`. Users might pass just the account URL, or include the `/api/3` suffix. The client normalizes both:

```python
base_url = base_url.rstrip("/")
if not base_url.endswith("/api/3"):
    base_url = f"{base_url}/api/3"
```

Small thing, but it eliminates a common setup failure.

### Read-Only Automations (And Being Honest About It)

ActiveCampaign's API doesn't support creating automations programmatically — you can only list them, view details, and add contacts to existing ones. The tool docstrings say this explicitly:

```python
@mcp.tool()
async def list_automations(...) -> str:
    """List automations (read-only — AC API doesn't support creating automations)."""
```

When the AI knows the boundary, it can suggest alternatives ("Create the automation in the AC dashboard, then I can add contacts to it") instead of failing mysteriously.

## Get Started in 2 Minutes

### Install

```bash
pip install mcp-activecampaign
```

### Get Your API Credentials

ActiveCampaign → Settings → Developer. You need:
- **API URL**: `https://youraccountname.api-us1.com`
- **API Key**: The key shown on that page

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "activecampaign": {
      "command": "mcp-activecampaign",
      "env": {
        "ACTIVECAMPAIGN_URL": "https://youraccountname.api-us1.com",
        "ACTIVECAMPAIGN_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add activecampaign -- env ACTIVECAMPAIGN_URL=https://youraccountname.api-us1.com ACTIVECAMPAIGN_API_KEY=key mcp-activecampaign
```

### Cursor

Same JSON config as Claude Desktop in `.cursor/mcp.json`.

## What I'd Do Differently

**Add deal note support.** ActiveCampaign deals have a notes system that's heavily used by sales teams. I covered the core CRUD but skipped notes — they're high-value for AI-assisted sales workflows.

**Build contact-to-deal linking tools.** The current `create_deal` accepts a `contact_id`, but there's no tool to view or manage the contact-deal association after creation. That relationship is central to how AC users think about their CRM.

## Lessons for MCP Server Builders

1. **Rate limit proactively, not reactively.** Client-side throttling is always better than hitting limits and retrying. Use `asyncio.Lock` + `time.monotonic()` for a clean implementation.
2. **Translate internal naming to user naming.** If the API calls something "dealGroups" but users call it "pipelines," use the user's word in your tools. The translation is invisible and the ergonomics improve dramatically.
3. **Document API limitations in docstrings.** If the platform doesn't support creating a resource via API, say so in the tool description. The AI uses docstrings to decide what to suggest.
4. **Be the first mover.** When you search for "[Platform] MCP server" and find zero results, that's a signal. 185K customers and nobody built this? Ship it.

## Links

- **GitHub**: [AlexlaGuardia/mcp-activecampaign](https://github.com/AlexlaGuardia/mcp-activecampaign)
- **PyPI**: [mcp-activecampaign](https://pypi.org/project/mcp-activecampaign/)
- **License**: MIT

---

*This is part of a series of production-grade MCP servers I'm building for underserved SaaS platforms. Also available: [Mailchimp](https://github.com/AlexlaGuardia/mcp-mailchimp), [WooCommerce](https://github.com/AlexlaGuardia/mcp-woocommerce), [FreshBooks](https://github.com/AlexlaGuardia/mcp-freshbooks). Follow me here or on [GitHub](https://github.com/AlexlaGuardia) to catch the next one.*
