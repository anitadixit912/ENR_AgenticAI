"""SAP supplier and purchase order lookup tools via MCP."""
import logging
from langchain.tools import tool
from mcp_tools import get_mcp_tools

logger = logging.getLogger(__name__)

_mcp_tools_cache = None


async def _get_mcp():
    global _mcp_tools_cache
    if _mcp_tools_cache is None:
        _mcp_tools_cache = await get_mcp_tools()
    return _mcp_tools_cache


def _find_tool(tools, name_fragment):
    for t in tools:
        if name_fragment.lower() in t.name.lower():
            return t
    return None


@tool
def get_suppliers_by_region(country_codes: list) -> list:
    """Retrieve active SAP suppliers located in the given country codes via MCP.
    
    Args:
        country_codes: List of ISO country codes (e.g. ['UA', 'RU', 'IL'])
    
    Returns:
        List of supplier dicts: supplier_id, name, country, city, postal_code
    """
    import asyncio

    async def _run():
        try:
            tools = await _get_mcp()
            bp_tool = _find_tool(tools, "BusinessPartner") or _find_tool(tools, "business_partner")
            if not bp_tool:
                logger.warning("Business Partner MCP tool not found â returning empty supplier list")
                return []

            country_filter = " or ".join(f"BusinessPartnerCountry eq '{c}'" for c in country_codes[:20])
            filter_str = f"({country_filter}) and BusinessPartnerCategory eq '2'"
            result = await bp_tool.arun({
                "$filter": filter_str,
                "$select": "BusinessPartner,BusinessPartnerFullName,BusinessPartnerCountry,CityName,PostalCode",
                "$top": 100
            })

            suppliers = []
            items = result if isinstance(result, list) else result.get("value", [])
            for item in items[:100]:
                suppliers.append({
                    "supplier_id": item.get("BusinessPartner", ""),
                    "name": item.get("BusinessPartnerFullName", ""),
                    "country": item.get("BusinessPartnerCountry", ""),
                    "city": item.get("CityName", ""),
                    "postal_code": item.get("PostalCode", "")
                })
            logger.info("Supplier lookup: %d suppliers found for countries %s", len(suppliers), country_codes)
            return suppliers
        except Exception as e:
            logger.error("Supplier lookup failed â %s", str(e))
            return []

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run())
                return future.result(timeout=30)
        return loop.run_until_complete(_run())
    except Exception as e:
        logger.error("Supplier lookup error â %s", str(e))
        return []


@tool
def get_open_pos_by_supplier(supplier_ids: list) -> list:
    """Retrieve open purchase orders for the given supplier IDs via MCP.
    
    Args:
        supplier_ids: List of SAP supplier IDs
    
    Returns:
        List of PO dicts: po_number, supplier_id, material, net_value, currency, delivery_date, plant
    """
    import asyncio

    async def _run():
        try:
            tools = await _get_mcp()
            po_tool = _find_tool(tools, "PurchaseOrder") or _find_tool(tools, "purchase_order")
            if not po_tool:
                logger.warning("Purchase Order MCP tool not found â returning empty PO list")
                return []

            supplier_filter = " or ".join(f"Supplier eq '{s}'" for s in supplier_ids[:20])
            filter_str = f"({supplier_filter}) and PurchaseOrderStatus ne 'CLOSED'"
            result = await po_tool.arun({
                "$filter": filter_str,
                "$select": "PurchaseOrder,Supplier,Material,NetPriceAmount,DocumentCurrency,ScheduleLine,Plant",
                "$top": 100
            })

            pos = []
            items = result if isinstance(result, list) else result.get("value", [])
            for item in items[:100]:
                pos.append({
                    "po_number": item.get("PurchaseOrder", ""),
                    "supplier_id": item.get("Supplier", ""),
                    "material": item.get("Material", ""),
                    "net_value": float(item.get("NetPriceAmount", 0) or 0),
                    "currency": item.get("DocumentCurrency", "USD"),
                    "delivery_date": item.get("ScheduleLine", ""),
                    "plant": item.get("Plant", "")
                })
            logger.info("PO lookup: %d open POs found for %d suppliers", len(pos), len(supplier_ids))
            return pos
        except Exception as e:
            logger.error("PO lookup failed â %s", str(e))
            return []

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run())
                return future.result(timeout=30)
        return loop.run_until_complete(_run())
    except Exception as e:
        logger.error("PO lookup error â %s", str(e))
        return []
