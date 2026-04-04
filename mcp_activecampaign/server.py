"""MCP server for the ActiveCampaign API — 51 tools."""

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_activecampaign.client import ActiveCampaignClient, ActiveCampaignError

mcp = FastMCP(
    "mcp-activecampaign",
    instructions=(
        "Production-grade MCP server for the ActiveCampaign API. "
        "51 tools for contacts, deals, tags, lists, automations, "
        "pipelines, campaigns, custom fields, accounts, webhooks, "
        "notes, tasks, event tracking, ecommerce, and bulk operations."
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
# CONTACT NOTES (CRM)
# ============================================================================


@mcp.tool()
async def list_contact_notes(contact_id: str, limit: int = 20, offset: int = 0) -> str:
    """List notes on a contact -- CRM-style internal notes attached to a person."""
    ac = get_client()
    data = await ac.get(
        f"/contacts/{contact_id}/notes",
        params={"limit": min(limit, 100), "offset": offset},
    )
    notes = []
    for n in data.get("notes", []):
        notes.append({
            "id": n.get("id", ""),
            "note": n.get("note", ""),
            "created_by": n.get("userid", ""),
            "created_at": n.get("cdate", ""),
            "updated_at": n.get("mdate", ""),
        })
    return _fmt({"contact_id": contact_id, "total": _total(data), "notes": notes})


@mcp.tool()
async def add_contact_note(contact_id: str, note: str) -> str:
    """Add a note to a contact -- useful for logging calls, meetings, or follow-ups."""
    ac = get_client()
    data = await ac.post(
        f"/contacts/{contact_id}/notes",
        json={"note": {"note": note}},
    )
    n = data.get("note", {})
    return _fmt({
        "id": n.get("id", ""),
        "contact_id": contact_id,
        "note": n.get("note", ""),
        "created_at": n.get("cdate", ""),
        "message": "Note added.",
    })


# ============================================================================
# DEAL NOTES
# ============================================================================


@mcp.tool()
async def list_deal_notes(deal_id: str, limit: int = 20, offset: int = 0) -> str:
    """List notes on a deal -- internal annotations for the sales pipeline."""
    ac = get_client()
    data = await ac.get(
        f"/deals/{deal_id}/notes",
        params={"limit": min(limit, 100), "offset": offset},
    )
    notes = []
    for n in data.get("notes", []):
        notes.append({
            "id": n.get("id", ""),
            "note": n.get("note", ""),
            "created_by": n.get("userid", ""),
            "created_at": n.get("cdate", ""),
        })
    return _fmt({"deal_id": deal_id, "total": _total(data), "notes": notes})


@mcp.tool()
async def add_deal_note(deal_id: str, note: str) -> str:
    """Add a note to a deal -- log updates, negotiation details, or next steps."""
    ac = get_client()
    data = await ac.post(
        f"/deals/{deal_id}/notes",
        json={"note": {"note": note}},
    )
    n = data.get("note", {})
    return _fmt({
        "id": n.get("id", ""),
        "deal_id": deal_id,
        "note": n.get("note", ""),
        "message": "Deal note added.",
    })


# ============================================================================
# TASKS (CRM)
# ============================================================================


@mcp.tool()
async def list_tasks(limit: int = 20, offset: int = 0, deal_id: str = "", contact_id: str = "") -> str:
    """List CRM tasks. Optionally filter by deal_id or contact_id."""
    ac = get_client()
    params: dict[str, Any] = {"limit": min(limit, 100), "offset": offset}
    if deal_id:
        params["filters[dealTasktype]"] = "1"
        params["filters[relid]"] = deal_id
    data = await ac.get("/dealTasks", params=params)
    tasks = []
    for t in data.get("dealTasks", []):
        tasks.append({
            "id": t.get("id", ""),
            "title": t.get("title", ""),
            "note": t.get("note", ""),
            "due_date": t.get("duedate", ""),
            "status": t.get("status", ""),
            "deal_id": t.get("relid", ""),
            "assignee": t.get("assignee", ""),
            "type": t.get("dealTasktype", ""),
            "created_at": t.get("cdate", ""),
        })
    return _fmt({"total": _total(data), "tasks": tasks})


@mcp.tool()
async def create_task(
    title: str,
    deal_id: str,
    due_date: str = "",
    note: str = "",
    task_type: str = "1",
    assignee_id: str = "",
) -> str:
    """Create a CRM task on a deal. due_date: ISO 8601 (e.g. '2026-04-10T14:00:00'). task_type: 1=call, 2=email, 3=to-do."""
    ac = get_client()
    task: dict[str, Any] = {
        "title": title,
        "relid": deal_id,
        "reltype": "deal",
        "dealTasktype": task_type,
        "status": "0",
    }
    if due_date:
        task["duedate"] = due_date
    if note:
        task["note"] = note
    if assignee_id:
        task["assignee"] = assignee_id
    data = await ac.post("/dealTasks", json={"dealTask": task})
    t = data.get("dealTask", {})
    return _fmt({
        "id": t.get("id", ""),
        "title": t.get("title", ""),
        "deal_id": deal_id,
        "due_date": t.get("duedate", ""),
        "message": "Task created.",
    })


@mcp.tool()
async def update_task(
    task_id: str,
    title: str = "",
    due_date: str = "",
    note: str = "",
    status: str = "",
) -> str:
    """Update a CRM task. status: 0=incomplete, 1=complete."""
    ac = get_client()
    task: dict[str, Any] = {}
    if title:
        task["title"] = title
    if due_date:
        task["duedate"] = due_date
    if note:
        task["note"] = note
    if status:
        task["status"] = status
    if not task:
        return "No fields provided to update."
    data = await ac.put(f"/dealTasks/{task_id}", json={"dealTask": task})
    t = data.get("dealTask", {})
    return _fmt({
        "id": t.get("id", ""),
        "title": t.get("title", ""),
        "status": t.get("status", ""),
        "message": "Task updated.",
    })


@mcp.tool()
async def delete_task(task_id: str) -> str:
    """Delete a CRM task."""
    ac = get_client()
    await ac.delete(f"/dealTasks/{task_id}")
    return _fmt({"task_id": task_id, "message": "Task deleted."})


# ============================================================================
# LIST MEMBERSHIP (subscribe/unsubscribe)
# ============================================================================


@mcp.tool()
async def subscribe_contact_to_list(contact_id: str, list_id: str, status: str = "1") -> str:
    """Subscribe a contact to a list. status: 1=subscribed, 2=unsubscribed."""
    ac = get_client()
    data = await ac.post(
        "/contactLists",
        json={"contactList": {"list": list_id, "contact": contact_id, "status": status}},
    )
    cl = data.get("contactList", {})
    return _fmt({
        "contact_id": contact_id,
        "list_id": list_id,
        "status": cl.get("status", ""),
        "message": "Contact subscribed to list.",
    })


@mcp.tool()
async def unsubscribe_contact_from_list(contact_id: str, list_id: str) -> str:
    """Unsubscribe a contact from a list."""
    ac = get_client()
    data = await ac.post(
        "/contactLists",
        json={"contactList": {"list": list_id, "contact": contact_id, "status": "2"}},
    )
    return _fmt({
        "contact_id": contact_id,
        "list_id": list_id,
        "message": "Contact unsubscribed from list.",
    })


# ============================================================================
# AUTOMATION MANAGEMENT (remove, list contact automations)
# ============================================================================


@mcp.tool()
async def remove_contact_from_automation(contact_automation_id: str) -> str:
    """Remove a contact from an automation. Get the contact_automation_id from list_contact_automations."""
    ac = get_client()
    await ac.delete(f"/contactAutomations/{contact_automation_id}")
    return _fmt({"contact_automation_id": contact_automation_id, "message": "Contact removed from automation."})


@mcp.tool()
async def list_contact_automations(contact_id: str) -> str:
    """List all automations a contact is currently enrolled in."""
    ac = get_client()
    data = await ac.get(
        "/contactAutomations",
        params={"filters[contact]": contact_id, "limit": 100},
    )
    automations = []
    for ca in data.get("contactAutomations", []):
        automations.append({
            "id": ca.get("id", ""),
            "automation_id": ca.get("automation", ""),
            "status": ca.get("status", ""),
            "add_date": ca.get("adddate", ""),
            "last_date": ca.get("lastdate", ""),
            "completed": ca.get("completedElements", "0"),
            "total_elements": ca.get("totalElements", "0"),
        })
    return _fmt({"contact_id": contact_id, "total": len(automations), "automations": automations})


# ============================================================================
# EVENT TRACKING
# ============================================================================


@mcp.tool()
async def track_event(event_name: str, contact_email: str, event_data: str = "") -> str:
    """Track a custom event for a contact -- triggers behavior-based automations. event_data: optional value string."""
    ac = get_client()
    # AC event tracking uses a different endpoint pattern
    data = await ac.post(
        "/tracking/event",
        json={"event": event_name, "email": contact_email, "eventdata": event_data},
    )
    return _fmt({
        "event": event_name,
        "email": contact_email,
        "message": "Event tracked.",
    })


@mcp.tool()
async def track_site_event(contact_email: str, url: str) -> str:
    """Track a site visit for a contact -- logs that they visited a specific URL."""
    ac = get_client()
    data = await ac.post(
        "/tracking/site",
        json={"email": contact_email, "url": url},
    )
    return _fmt({
        "email": contact_email,
        "url": url,
        "message": "Site visit tracked.",
    })


# ============================================================================
# ECOMMERCE
# ============================================================================


@mcp.tool()
async def list_ecommerce_connections(limit: int = 20) -> str:
    """List connected e-commerce platforms (Shopify, WooCommerce, BigCommerce, etc.)."""
    ac = get_client()
    data = await ac.get("/connections", params={"limit": min(limit, 100)})
    connections = []
    for c in data.get("connections", []):
        connections.append({
            "id": c.get("id", ""),
            "name": c.get("name", ""),
            "service": c.get("service", ""),
            "external_id": c.get("externalid", ""),
            "status": c.get("status", ""),
            "link_url": c.get("linkUrl", ""),
            "is_internal": c.get("isInternal", ""),
        })
    return _fmt({"total": _total(data), "connections": connections})


@mcp.tool()
async def list_ecommerce_orders(
    limit: int = 20,
    offset: int = 0,
    email: str = "",
    connection_id: str = "",
) -> str:
    """List e-commerce orders. Filter by customer email or connection_id for revenue tracking."""
    ac = get_client()
    params: dict[str, Any] = {"limit": min(limit, 100), "offset": offset}
    if email:
        params["filters[email]"] = email
    if connection_id:
        params["filters[connectionid]"] = connection_id
    data = await ac.get("/ecomOrders", params=params)
    orders = []
    for o in data.get("ecomOrders", []):
        orders.append({
            "id": o.get("id", ""),
            "external_id": o.get("externalid", ""),
            "email": o.get("email", ""),
            "total_price": o.get("totalPrice", "0"),
            "currency": o.get("currency", ""),
            "order_number": o.get("orderNumber", ""),
            "order_date": o.get("orderDate", ""),
            "connection_id": o.get("connectionid", ""),
            "source": o.get("source", ""),
            "created_at": o.get("createdDate", ""),
        })
    return _fmt({"total": _total(data), "orders": orders})


@mcp.tool()
async def get_ecommerce_order(order_id: str) -> str:
    """Get full details for a specific e-commerce order including line items."""
    ac = get_client()
    data = await ac.get(f"/ecomOrders/{order_id}")
    o = data.get("ecomOrder", {})
    products = []
    for p in data.get("ecomOrderProducts", []):
        products.append({
            "name": p.get("name", ""),
            "price": p.get("price", "0"),
            "quantity": p.get("quantity", "0"),
            "sku": p.get("sku", ""),
            "category": p.get("category", ""),
        })
    return _fmt({
        "id": o.get("id", ""),
        "external_id": o.get("externalid", ""),
        "email": o.get("email", ""),
        "total_price": o.get("totalPrice", "0"),
        "currency": o.get("currency", ""),
        "order_number": o.get("orderNumber", ""),
        "order_url": o.get("orderUrl", ""),
        "order_date": o.get("orderDate", ""),
        "shipping_method": o.get("shippingMethod", ""),
        "products": products,
    })


# ============================================================================
# BULK OPERATIONS
# ============================================================================


@mcp.tool()
async def bulk_import_contacts(contacts_json: str, list_id: str = "", tag_id: str = "") -> str:
    """Bulk import contacts. contacts_json: JSON array of {email, first_name, last_name, phone}. Optionally add to a list or tag."""
    ac = get_client()
    import json as _json
    try:
        contacts = _json.loads(contacts_json)
    except _json.JSONDecodeError:
        return "Invalid JSON. Provide an array of {email, first_name, last_name} objects."
    if not isinstance(contacts, list):
        return "contacts_json must be a JSON array."
    payload: dict[str, Any] = {"contacts": []}
    for c in contacts[:250]:
        entry: dict[str, Any] = {"email": c.get("email", "")}
        if c.get("first_name"):
            entry["first_name"] = c["first_name"]
        if c.get("last_name"):
            entry["last_name"] = c["last_name"]
        if c.get("phone"):
            entry["phone"] = c["phone"]
        payload["contacts"].append(entry)
    if list_id:
        payload["list"] = list_id
    if tag_id:
        payload["tag"] = tag_id
    data = await ac.post("/import/bulk_import", json=payload)
    return _fmt({
        "queued": len(payload["contacts"]),
        "message": data.get("message", "Bulk import queued."),
    })


# ============================================================================
# ENTRY POINT
# ============================================================================


def main() -> None:
    standby_port = os.environ.get("ACTOR_STANDBY_PORT")
    if standby_port:
        os.environ.setdefault("FASTMCP_HOST", "0.0.0.0")
        os.environ.setdefault("FASTMCP_PORT", standby_port)
        os.environ.setdefault("FASTMCP_STREAMABLE_HTTP_PATH", "/mcp")
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
