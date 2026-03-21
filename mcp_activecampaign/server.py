"""MCP server for the ActiveCampaign API — 30+ tools."""

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_activecampaign.client import ActiveCampaignClient, ActiveCampaignError

mcp = FastMCP(
    "mcp-activecampaign",
    instructions=(
        "Production-grade MCP server for the ActiveCampaign API. "
        "30+ tools for contacts, deals, tags, lists, automations, "
        "pipelines, campaigns, custom fields, accounts, and webhooks."
    ),
)

# -- Client singleton --------------------------------------------------------

_client: ActiveCampaignClient | None = None


def get_client() -> ActiveCampaignClient:
    global _client
    if _client is None:
        base_url = os.environ.get("ACTIVECAMPAIGN_URL", "")
        api_key = os.environ.get("ACTIVECAMPAIGN_API_KEY", "")
        if not base_url:
            raise ValueError(
                "ACTIVECAMPAIGN_URL environment variable required. "
                "Find it at Settings > Developer in your ActiveCampaign account."
            )
        if not api_key:
            raise ValueError(
                "ACTIVECAMPAIGN_API_KEY environment variable required. "
                "Find it at Settings > Developer in your ActiveCampaign account."
            )
        _client = ActiveCampaignClient(base_url, api_key)
    return _client


def _fmt(data: Any) -> str:
    """Format response data as indented JSON string."""
    return json.dumps(data, indent=2, default=str)


def _total(data: dict) -> int:
    """Extract total count from AC meta (returns string, we cast)."""
    meta = data.get("meta", {})
    return int(meta.get("total", "0"))


# ============================================================================
# ACCOUNT
# ============================================================================


@mcp.tool()
async def ping() -> str:
    """Validate your ActiveCampaign API connection and get account info."""
    ac = get_client()
    try:
        data = await ac.get("/accounts")
        return _fmt({
            "status": "connected",
            "total_accounts": _total(data),
            "message": "ActiveCampaign API connection successful.",
        })
    except ActiveCampaignError as e:
        return f"Connection failed: {e}"


# ============================================================================
# CONTACTS
# ============================================================================


@mcp.tool()
async def list_contacts(
    limit: int = 20,
    offset: int = 0,
    email: str = "",
    list_id: str = "",
    tag_id: str = "",
    status: str = "",
) -> str:
    """List contacts. Filter by email, list_id, tag_id, or status (-1=any, 0=unconfirmed, 1=active, 2=unsubscribed, 3=bounced)."""
    ac = get_client()
    params: dict[str, Any] = {"limit": min(limit, 100), "offset": offset}
    if email:
        params["email"] = email
    if list_id:
        params["listid"] = list_id
    if tag_id:
        params["tagid"] = tag_id
    if status:
        params["status"] = status
    data = await ac.get("/contacts", params=params)
    contacts = []
    for c in data.get("contacts", []):
        contacts.append({
            "id": c["id"],
            "email": c.get("email", ""),
            "first_name": c.get("firstName", ""),
            "last_name": c.get("lastName", ""),
            "phone": c.get("phone", ""),
            "created_at": c.get("cdate", ""),
            "updated_at": c.get("udate", ""),
        })
    return _fmt({"total": _total(data), "contacts": contacts})


@mcp.tool()
async def get_contact(contact_id: str) -> str:
    """Get full details for a specific contact by ID."""
    ac = get_client()
    data = await ac.get(f"/contacts/{contact_id}")
    c = data.get("contact", {})
    return _fmt({
        "id": c.get("id", ""),
        "email": c.get("email", ""),
        "first_name": c.get("firstName", ""),
        "last_name": c.get("lastName", ""),
        "phone": c.get("phone", ""),
        "tags": [t.get("tag", "") for t in data.get("contactTags", [])],
        "lists": [
            {"id": cl.get("list", ""), "status": cl.get("status", "")}
            for cl in data.get("contactLists", [])
        ],
        "deals": [d.get("id", "") for d in data.get("deals", [])],
        "ip": c.get("ip", ""),
        "created_at": c.get("cdate", ""),
        "updated_at": c.get("udate", ""),
    })


@mcp.tool()
async def create_contact(
    email: str,
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
) -> str:
    """Create a new contact. Email is required."""
    ac = get_client()
    contact: dict[str, str] = {"email": email}
    if first_name:
        contact["firstName"] = first_name
    if last_name:
        contact["lastName"] = last_name
    if phone:
        contact["phone"] = phone
    data = await ac.post("/contacts", json={"contact": contact})
    c = data.get("contact", {})
    return _fmt({
        "id": c.get("id", ""),
        "email": c.get("email", ""),
        "message": "Contact created.",
    })


@mcp.tool()
async def update_contact(
    contact_id: str,
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
) -> str:
    """Update a contact. Only provide fields you want to change."""
    ac = get_client()
    contact: dict[str, str] = {}
    if email:
        contact["email"] = email
    if first_name:
        contact["firstName"] = first_name
    if last_name:
        contact["lastName"] = last_name
    if phone:
        contact["phone"] = phone
    if not contact:
        return "No fields provided to update."
    data = await ac.put(f"/contacts/{contact_id}", json={"contact": contact})
    c = data.get("contact", {})
    return _fmt({
        "id": c.get("id", ""),
        "email": c.get("email", ""),
        "updated_fields": list(contact.keys()),
        "message": "Contact updated.",
    })


@mcp.tool()
async def delete_contact(contact_id: str) -> str:
    """Permanently delete a contact by ID."""
    ac = get_client()
    await ac.delete(f"/contacts/{contact_id}")
    return _fmt({"contact_id": contact_id, "message": "Contact deleted."})


@mcp.tool()
async def search_contacts(query: str, limit: int = 20) -> str:
    """Search contacts by email address (partial match supported)."""
    ac = get_client()
    data = await ac.get(
        "/contacts",
        params={"search": query, "limit": min(limit, 100)},
    )
    contacts = []
    for c in data.get("contacts", []):
        contacts.append({
            "id": c["id"],
            "email": c.get("email", ""),
            "first_name": c.get("firstName", ""),
            "last_name": c.get("lastName", ""),
        })
    return _fmt({"total": _total(data), "contacts": contacts})


# ============================================================================
# DEALS
# ============================================================================


@mcp.tool()
async def list_deals(
    limit: int = 20,
    offset: int = 0,
    stage_id: str = "",
    pipeline_id: str = "",
) -> str:
    """List deals. Optionally filter by stage_id or pipeline_id (called 'group' in AC)."""
    ac = get_client()
    params: dict[str, Any] = {"limit": min(limit, 100), "offset": offset}
    if stage_id:
        params["filters[stage]"] = stage_id
    if pipeline_id:
        params["filters[group]"] = pipeline_id
    data = await ac.get("/deals", params=params)
    deals = []
    for d in data.get("deals", []):
        deals.append({
            "id": d["id"],
            "title": d.get("title", ""),
            "value": d.get("value", "0"),
            "currency": d.get("currency", "usd"),
            "stage": d.get("stage", ""),
            "pipeline": d.get("group", ""),
            "owner": d.get("owner", ""),
            "status": d.get("status", ""),
            "created_at": d.get("cdate", ""),
        })
    return _fmt({"total": _total(data), "deals": deals})


@mcp.tool()
async def get_deal(deal_id: str) -> str:
    """Get full details for a specific deal."""
    ac = get_client()
    data = await ac.get(f"/deals/{deal_id}")
    d = data.get("deal", {})
    return _fmt({
        "id": d.get("id", ""),
        "title": d.get("title", ""),
        "value": d.get("value", "0"),
        "currency": d.get("currency", "usd"),
        "stage": d.get("stage", ""),
        "pipeline": d.get("group", ""),
        "owner": d.get("owner", ""),
        "status": d.get("status", ""),
        "description": d.get("description", ""),
        "contact": d.get("contact", ""),
        "percent": d.get("percent", ""),
        "created_at": d.get("cdate", ""),
        "updated_at": d.get("mdate", ""),
    })


@mcp.tool()
async def create_deal(
    title: str,
    value: int,
    pipeline_id: str,
    stage_id: str,
    contact_id: str = "",
    currency: str = "usd",
    description: str = "",
    owner_id: str = "",
    percent: int = 0,
) -> str:
    """Create a new deal. Value is in cents (e.g. 10000 = $100.00)."""
    ac = get_client()
    deal: dict[str, Any] = {
        "title": title,
        "value": value,
        "group": pipeline_id,
        "stage": stage_id,
        "currency": currency,
    }
    if contact_id:
        deal["contact"] = contact_id
    if description:
        deal["description"] = description
    if owner_id:
        deal["owner"] = owner_id
    if percent:
        deal["percent"] = percent
    data = await ac.post("/deals", json={"deal": deal})
    d = data.get("deal", {})
    return _fmt({
        "id": d.get("id", ""),
        "title": d.get("title", ""),
        "value": d.get("value", ""),
        "message": "Deal created.",
    })


@mcp.tool()
async def update_deal(
    deal_id: str,
    title: str = "",
    value: int = 0,
    stage_id: str = "",
    pipeline_id: str = "",
    status: str = "",
    description: str = "",
    owner_id: str = "",
    percent: int = -1,
) -> str:
    """Update a deal. Status: 0=open, 1=won, 2=lost. Only provide fields to change."""
    ac = get_client()
    deal: dict[str, Any] = {}
    if title:
        deal["title"] = title
    if value:
        deal["value"] = value
    if stage_id:
        deal["stage"] = stage_id
    if pipeline_id:
        deal["group"] = pipeline_id
    if status:
        deal["status"] = status
    if description:
        deal["description"] = description
    if owner_id:
        deal["owner"] = owner_id
    if percent >= 0:
        deal["percent"] = percent
    if not deal:
        return "No fields provided to update."
    data = await ac.put(f"/deals/{deal_id}", json={"deal": deal})
    d = data.get("deal", {})
    return _fmt({
        "id": d.get("id", ""),
        "title": d.get("title", ""),
        "updated_fields": list(deal.keys()),
        "message": "Deal updated.",
    })


@mcp.tool()
async def delete_deal(deal_id: str) -> str:
    """Permanently delete a deal."""
    ac = get_client()
    await ac.delete(f"/deals/{deal_id}")
    return _fmt({"deal_id": deal_id, "message": "Deal deleted."})


# ============================================================================
# TAGS
# ============================================================================


@mcp.tool()
async def list_tags(limit: int = 100, offset: int = 0, search: str = "") -> str:
    """List all tags. Optionally search by name."""
    ac = get_client()
    params: dict[str, Any] = {"limit": min(limit, 100), "offset": offset}
    if search:
        params["search"] = search
    data = await ac.get("/tags", params=params)
    tags = []
    for t in data.get("tags", []):
        tags.append({
            "id": t["id"],
            "tag": t.get("tag", ""),
            "type": t.get("tagType", ""),
            "description": t.get("description", ""),
        })
    return _fmt({"total": _total(data), "tags": tags})


@mcp.tool()
async def create_tag(tag_name: str, tag_type: str = "contact", description: str = "") -> str:
    """Create a new tag. tag_type: contact or deal."""
    ac = get_client()
    body = {"tag": tag_name, "tagType": tag_type}
    if description:
        body["description"] = description
    data = await ac.post("/tags", json={"tag": body})
    t = data.get("tag", {})
    return _fmt({
        "id": t.get("id", ""),
        "tag": t.get("tag", ""),
        "message": "Tag created.",
    })


@mcp.tool()
async def add_tag_to_contact(contact_id: str, tag_id: str) -> str:
    """Add a tag to a contact."""
    ac = get_client()
    data = await ac.post(
        "/contactTags",
        json={"contactTag": {"contact": contact_id, "tag": tag_id}},
    )
    ct = data.get("contactTag", {})
    return _fmt({
        "id": ct.get("id", ""),
        "contact": contact_id,
        "tag": tag_id,
        "message": "Tag added to contact.",
    })


@mcp.tool()
async def remove_tag_from_contact(contact_tag_id: str) -> str:
    """Remove a tag from a contact. Use the contactTag ID (from get_contact or add_tag_to_contact)."""
    ac = get_client()
    await ac.delete(f"/contactTags/{contact_tag_id}")
    return _fmt({"contact_tag_id": contact_tag_id, "message": "Tag removed from contact."})


# ============================================================================
# LISTS
# ============================================================================


@mcp.tool()
async def list_lists(limit: int = 20, offset: int = 0) -> str:
    """List all mailing lists."""
    ac = get_client()
    data = await ac.get("/lists", params={"limit": min(limit, 100), "offset": offset})
    lists = []
    for li in data.get("lists", []):
        lists.append({
            "id": li["id"],
            "name": li.get("name", ""),
            "subscriber_count": li.get("subscriber_count", 0),
            "sender_url": li.get("sender_url", ""),
            "created_at": li.get("cdate", ""),
        })
    return _fmt({"total": _total(data), "lists": lists})


@mcp.tool()
async def get_list(list_id: str) -> str:
    """Get details for a specific mailing list."""
    ac = get_client()
    data = await ac.get(f"/lists/{list_id}")
    li = data.get("list", {})
    return _fmt({
        "id": li.get("id", ""),
        "name": li.get("name", ""),
        "sender_name": li.get("sender_name", ""),
        "sender_addr": li.get("sender_addr", ""),
        "sender_url": li.get("sender_url", ""),
        "subscriber_count": li.get("subscriber_count", 0),
        "created_at": li.get("cdate", ""),
    })


# ============================================================================
# AUTOMATIONS
# ============================================================================


@mcp.tool()
async def list_automations(limit: int = 20, offset: int = 0) -> str:
    """List automations (read-only — AC API doesn't support creating automations)."""
    ac = get_client()
    data = await ac.get(
        "/automations",
        params={"limit": min(limit, 100), "offset": offset},
    )
    automations = []
    for a in data.get("automations", []):
        automations.append({
            "id": a["id"],
            "name": a.get("name", ""),
            "status": a.get("status", ""),
            "entered": a.get("entered", "0"),
            "exited": a.get("exited", "0"),
            "hidden": a.get("hidden", ""),
            "created_at": a.get("cdate", ""),
            "updated_at": a.get("mdate", ""),
        })
    return _fmt({"total": _total(data), "automations": automations})


@mcp.tool()
async def get_automation(automation_id: str) -> str:
    """Get details for a specific automation."""
    ac = get_client()
    data = await ac.get(f"/automations/{automation_id}")
    a = data.get("automation", {})
    return _fmt({
        "id": a.get("id", ""),
        "name": a.get("name", ""),
        "status": a.get("status", ""),
        "entered": a.get("entered", "0"),
        "exited": a.get("exited", "0"),
        "created_at": a.get("cdate", ""),
        "updated_at": a.get("mdate", ""),
    })


@mcp.tool()
async def add_contact_to_automation(contact_id: str, automation_id: str) -> str:
    """Add a contact to an automation."""
    ac = get_client()
    data = await ac.post(
        "/contactAutomations",
        json={"contactAutomation": {"contact": contact_id, "automation": automation_id}},
    )
    ca = data.get("contactAutomation", {})
    return _fmt({
        "id": ca.get("id", ""),
        "contact": contact_id,
        "automation": automation_id,
        "message": "Contact added to automation.",
    })


# ============================================================================
# PIPELINES & STAGES
# ============================================================================


@mcp.tool()
async def list_pipelines(limit: int = 20, offset: int = 0) -> str:
    """List deal pipelines (called 'deal groups' in AC API)."""
    ac = get_client()
    data = await ac.get(
        "/dealGroups",
        params={"limit": min(limit, 100), "offset": offset},
    )
    pipelines = []
    for p in data.get("dealGroups", []):
        pipelines.append({
            "id": p["id"],
            "title": p.get("title", ""),
            "currency": p.get("currency", ""),
            "stages": len(p.get("stages", [])),
            "created_at": p.get("cdate", ""),
        })
    return _fmt({"total": _total(data), "pipelines": pipelines})


@mcp.tool()
async def list_stages(pipeline_id: str = "", limit: int = 100, offset: int = 0) -> str:
    """List deal stages. Optionally filter by pipeline_id."""
    ac = get_client()
    params: dict[str, Any] = {"limit": min(limit, 100), "offset": offset}
    if pipeline_id:
        params["filters[d_groupid]"] = pipeline_id
    data = await ac.get("/dealStages", params=params)
    stages = []
    for s in data.get("dealStages", []):
        stages.append({
            "id": s["id"],
            "title": s.get("title", ""),
            "pipeline_id": s.get("group", ""),
            "order": s.get("order", ""),
            "deal_count": s.get("dealCount", "0"),
        })
    return _fmt({"total": _total(data), "stages": stages})


# ============================================================================
# CUSTOM FIELDS
# ============================================================================


@mcp.tool()
async def list_custom_fields(limit: int = 100, offset: int = 0) -> str:
    """List all contact custom fields."""
    ac = get_client()
    data = await ac.get("/fields", params={"limit": min(limit, 100), "offset": offset})
    fields = []
    for f in data.get("fields", []):
        fields.append({
            "id": f["id"],
            "title": f.get("title", ""),
            "type": f.get("type", ""),
            "perstag": f.get("perstag", ""),
            "options": f.get("options", []),
        })
    return _fmt({"total": _total(data), "fields": fields})


@mcp.tool()
async def get_field_values(contact_id: str) -> str:
    """Get all custom field values for a contact."""
    ac = get_client()
    data = await ac.get(
        "/fieldValues",
        params={"filters[contactid]": contact_id, "limit": 100},
    )
    values = []
    for fv in data.get("fieldValues", []):
        values.append({
            "id": fv.get("id", ""),
            "field_id": fv.get("field", ""),
            "value": fv.get("value", ""),
        })
    return _fmt({"contact_id": contact_id, "field_values": values})


@mcp.tool()
async def set_field_value(contact_id: str, field_id: str, value: str) -> str:
    """Set a custom field value for a contact."""
    ac = get_client()
    data = await ac.post(
        "/fieldValues",
        json={"fieldValue": {"contact": contact_id, "field": field_id, "value": value}},
    )
    fv = data.get("fieldValue", {})
    return _fmt({
        "id": fv.get("id", ""),
        "contact_id": contact_id,
        "field_id": field_id,
        "value": value,
        "message": "Field value set.",
    })


# ============================================================================
# CAMPAIGNS (read-only)
# ============================================================================


@mcp.tool()
async def list_campaigns(limit: int = 20, offset: int = 0) -> str:
    """List email campaigns (read-only — limited create support in AC API)."""
    ac = get_client()
    data = await ac.get(
        "/campaigns",
        params={"limit": min(limit, 100), "offset": offset},
    )
    campaigns = []
    for c in data.get("campaigns", []):
        campaigns.append({
            "id": c["id"],
            "name": c.get("name", ""),
            "type": c.get("type", ""),
            "status": c.get("status", ""),
            "send_date": c.get("sdate", ""),
            "total_sent": c.get("send_amt", "0"),
            "opens": c.get("uniqueopens", "0"),
            "clicks": c.get("uniquelinkclicks", "0"),
        })
    return _fmt({"total": _total(data), "campaigns": campaigns})


@mcp.tool()
async def get_campaign(campaign_id: str) -> str:
    """Get full details for a specific campaign."""
    ac = get_client()
    data = await ac.get(f"/campaigns/{campaign_id}")
    c = data.get("campaign", {})
    return _fmt({
        "id": c.get("id", ""),
        "name": c.get("name", ""),
        "type": c.get("type", ""),
        "status": c.get("status", ""),
        "subject": c.get("subject", ""),
        "from_name": c.get("fromname", ""),
        "from_email": c.get("fromemail", ""),
        "reply_to": c.get("reply2", ""),
        "send_date": c.get("sdate", ""),
        "total_sent": c.get("send_amt", "0"),
        "opens": c.get("uniqueopens", "0"),
        "clicks": c.get("uniquelinkclicks", "0"),
        "created_at": c.get("cdate", ""),
    })


# ============================================================================
# ACCOUNTS (B2B / Companies)
# ============================================================================


@mcp.tool()
async def list_accounts(limit: int = 20, offset: int = 0, search: str = "") -> str:
    """List accounts (companies). Optionally search by name."""
    ac = get_client()
    params: dict[str, Any] = {"limit": min(limit, 100), "offset": offset}
    if search:
        params["search"] = search
    data = await ac.get("/accounts", params=params)
    accounts = []
    for a in data.get("accounts", []):
        accounts.append({
            "id": a["id"],
            "name": a.get("name", ""),
            "account_url": a.get("accountUrl", ""),
            "created_at": a.get("createdTimestamp", ""),
            "updated_at": a.get("updatedTimestamp", ""),
        })
    return _fmt({"total": _total(data), "accounts": accounts})


@mcp.tool()
async def get_account(account_id: str) -> str:
    """Get details for a specific account (company)."""
    ac = get_client()
    data = await ac.get(f"/accounts/{account_id}")
    a = data.get("account", {})
    return _fmt({
        "id": a.get("id", ""),
        "name": a.get("name", ""),
        "account_url": a.get("accountUrl", ""),
        "contact_count": a.get("contactCount", "0"),
        "deal_count": a.get("dealCount", "0"),
        "created_at": a.get("createdTimestamp", ""),
        "updated_at": a.get("updatedTimestamp", ""),
    })


# ============================================================================
# WEBHOOKS
# ============================================================================


@mcp.tool()
async def list_webhooks(limit: int = 100, offset: int = 0) -> str:
    """List all registered webhooks."""
    ac = get_client()
    data = await ac.get(
        "/webhooks",
        params={"limit": min(limit, 100), "offset": offset},
    )
    webhooks = []
    for w in data.get("webhooks", []):
        webhooks.append({
            "id": w["id"],
            "name": w.get("name", ""),
            "url": w.get("url", ""),
            "events": w.get("events", []),
            "sources": w.get("sources", []),
            "list_id": w.get("listid", ""),
        })
    return _fmt({"total": _total(data), "webhooks": webhooks})


@mcp.tool()
async def create_webhook(
    name: str,
    url: str,
    events: str,
    list_id: str,
    sources: str = "public,admin,api,system",
) -> str:
    """Create a webhook. events: comma-separated (subscribe,unsubscribe,sent,open,click,bounce,deal_add,deal_update). sources: public,admin,api,system."""
    ac = get_client()
    event_list = [e.strip() for e in events.split(",") if e.strip()]
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    data = await ac.post(
        "/webhooks",
        json={
            "webhook": {
                "name": name,
                "url": url,
                "events": event_list,
                "sources": source_list,
                "listid": list_id,
            }
        },
    )
    w = data.get("webhook", {})
    return _fmt({
        "id": w.get("id", ""),
        "name": w.get("name", ""),
        "url": w.get("url", ""),
        "message": "Webhook created.",
    })


@mcp.tool()
async def delete_webhook(webhook_id: str) -> str:
    """Delete a webhook by ID."""
    ac = get_client()
    await ac.delete(f"/webhooks/{webhook_id}")
    return _fmt({"webhook_id": webhook_id, "message": "Webhook deleted."})


# ============================================================================
# ENTRY POINT
# ============================================================================


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
