# mcp-activecampaign

Production-grade MCP server for the ActiveCampaign API — **33 tools** for contacts, deals, automations, tags, pipelines, campaigns, custom fields, accounts, and webhooks.

The first MCP server for ActiveCampaign's 185,000+ customers.

## Features

- **Contacts** — List, get, create, update, delete, and search contacts
- **Deals** — Full CRM deal management with pipeline and stage support
- **Tags** — Create tags and manage contact-tag associations
- **Lists** — View mailing lists and subscriber counts
- **Automations** — List automations and add contacts to workflows
- **Pipelines & Stages** — View deal pipelines and their stages
- **Custom Fields** — List fields, get/set values per contact
- **Campaigns** — View email campaign details and performance metrics
- **Accounts** — Manage B2B company records
- **Webhooks** — Create, list, and delete webhook subscriptions
- **Rate limiting** — Built-in 5 req/s throttle (ActiveCampaign's limit)
- **Auto-retry** — Automatic retry on 429 responses

## Quick Start

### Install

```bash
pip install mcp-activecampaign
```

### Configure

Get your API URL and key from **Settings > Developer** in your ActiveCampaign account.

#### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

#### Environment Variables

```bash
export ACTIVECAMPAIGN_URL="https://youraccountname.api-us1.com"
export ACTIVECAMPAIGN_API_KEY="your-api-key"
mcp-activecampaign
```

## Tools (33)

| Category | Tools | Notes |
|----------|-------|-------|
| **Account** | `ping` | Connection test |
| **Contacts** | `list_contacts`, `get_contact`, `create_contact`, `update_contact`, `delete_contact`, `search_contacts` | Full CRUD + search |
| **Deals** | `list_deals`, `get_deal`, `create_deal`, `update_deal`, `delete_deal` | Full CRUD with pipeline/stage filters |
| **Tags** | `list_tags`, `create_tag`, `add_tag_to_contact`, `remove_tag_from_contact` | Contact tagging |
| **Lists** | `list_lists`, `get_list` | Mailing lists |
| **Automations** | `list_automations`, `get_automation`, `add_contact_to_automation` | Read + enroll (API limitation: can't create automations) |
| **Pipelines** | `list_pipelines`, `list_stages` | Deal pipeline structure |
| **Custom Fields** | `list_custom_fields`, `get_field_values`, `set_field_value` | Contact custom data |
| **Campaigns** | `list_campaigns`, `get_campaign` | Read-only (API limitation) |
| **Accounts** | `list_accounts`, `get_account` | B2B company records |
| **Webhooks** | `list_webhooks`, `create_webhook`, `delete_webhook` | Event subscriptions |

## API Notes

- **Auth**: API key via `Api-Token` header (no OAuth required)
- **Rate limit**: 5 requests/second per account (handled automatically)
- **Pagination**: Offset-based — all list tools support `limit` and `offset` params
- **Automations**: Read-only via API — you can list and enroll contacts, but can't create or edit workflows
- **Campaigns**: Mostly read-only via API — view details and metrics

## Development

```bash
git clone https://github.com/AlexlaGuardia/mcp-activecampaign.git
cd mcp-activecampaign
pip install -e ".[dev]"
pytest
```

## License

MIT
