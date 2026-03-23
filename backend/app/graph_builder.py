"""
Build a directed NetworkX graph from the SQLite O2C database.
Column names are camelCase as per the actual SAP dataset export.
"""

import json
import os
import sys
import sqlite3

import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH, GRAPH_CACHE, MAX_GRAPH_NODES
from app.db import table_exists


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    con = _con()

    # ── Sales Orders ─────────────────────────────────────────────
    if table_exists("sales_order_headers"):
        rows = con.execute(
            """SELECT salesOrder, soldToParty, totalNetAmount, transactionCurrency,
               creationDate, overallDeliveryStatus, overallOrdReltdBillgStatus
               FROM sales_order_headers LIMIT ?""",
            (MAX_GRAPH_NODES // 4,)
        ).fetchall()
        for r in rows:
            so = r["salesOrder"]
            if not so:
                continue
            nid = f"so_{so}"
            G.add_node(nid,
                type="SalesOrder",
                label=so,
                SalesOrder=so,
                SoldToParty=r["soldToParty"],
                TotalNetAmount=r["totalNetAmount"],
                Currency=r["transactionCurrency"],
                CreationDate=r["creationDate"],
                DeliveryStatus=r["overallDeliveryStatus"],
                BillingStatus=r["overallOrdReltdBillgStatus"],
            )

    # ── Sales Order Items ─────────────────────────────────────────
    if table_exists("sales_order_items"):
        rows = con.execute(
            """SELECT salesOrder, salesOrderItem, material,
               requestedQuantity, requestedQuantityUnit, netAmount
               FROM sales_order_items LIMIT ?""",
            (MAX_GRAPH_NODES // 3,)
        ).fetchall()
        for r in rows:
            so   = r["salesOrder"]
            item = r["salesOrderItem"]
            if not so or not item:
                continue
            nid = f"soitem_{so}_{item}"
            G.add_node(nid,
                type="SalesOrderItem",
                label=str(item),
                SalesOrder=so,
                Material=r["material"],
                Quantity=r["requestedQuantity"],
                Unit=r["requestedQuantityUnit"],
                NetAmount=r["netAmount"],
            )
            parent = f"so_{so}"
            if G.has_node(parent):
                G.add_edge(parent, nid, rel="HAS_ITEM")

    # ── Outbound Delivery Headers ─────────────────────────────────
    if table_exists("outbound_delivery_headers"):
        rows = con.execute(
            """SELECT deliveryDocument, actualGoodsMovementDate,
               overallGoodsMovementStatus, overallPickingStatus, shippingPoint
               FROM outbound_delivery_headers LIMIT ?""",
            (MAX_GRAPH_NODES // 4,)
        ).fetchall()
        for r in rows:
            doc = r["deliveryDocument"]
            if not doc:
                continue
            nid = f"del_{doc}"
            G.add_node(nid,
                type="OutboundDelivery",
                label=str(doc),
                DeliveryDocument=doc,
                DeliveryDate=r["actualGoodsMovementDate"],
                GoodsMovementStatus=r["overallGoodsMovementStatus"],
                PickingStatus=r["overallPickingStatus"],
                ShippingPoint=r["shippingPoint"],
            )

    # ── Link deliveries → sales orders ───────────────────────────
    if table_exists("outbound_delivery_items"):
        rows = con.execute(
            """SELECT DISTINCT deliveryDocument, referenceSdDocument
               FROM outbound_delivery_items
               WHERE referenceSdDocument IS NOT NULL AND referenceSdDocument != ''
               LIMIT ?""",
            (MAX_GRAPH_NODES // 2,)
        ).fetchall()
        for r in rows:
            del_nid = f"del_{r['deliveryDocument']}"
            so_nid  = f"so_{r['referenceSdDocument']}"
            if G.has_node(del_nid) and G.has_node(so_nid):
                G.add_edge(so_nid, del_nid, rel="HAS_DELIVERY")

    # ── Billing Document Headers ──────────────────────────────────
    if table_exists("billing_document_headers"):
        rows = con.execute(
            """SELECT billingDocument, billingDocumentType, totalNetAmount,
               transactionCurrency, billingDocumentDate, soldToParty,
               companyCode, accountingDocument
               FROM billing_document_headers LIMIT ?""",
            (MAX_GRAPH_NODES // 4,)
        ).fetchall()
        for r in rows:
            doc = r["billingDocument"]
            if not doc:
                continue
            nid = f"bill_{doc}"
            G.add_node(nid,
                type="BillingDocument",
                label=str(doc),
                BillingDocument=doc,
                DocType=r["billingDocumentType"],
                TotalNetAmount=r["totalNetAmount"],
                Currency=r["transactionCurrency"],
                BillingDate=r["billingDocumentDate"],
                SoldToParty=r["soldToParty"],
                AccountingDocument=r["accountingDocument"],
            )

    # ── Link billing → sales orders ───────────────────────────────
    if table_exists("billing_document_items"):
        rows = con.execute(
            """SELECT DISTINCT billingDocument, referenceSdDocument
               FROM billing_document_items
               WHERE referenceSdDocument IS NOT NULL AND referenceSdDocument != ''
               LIMIT ?""",
            (MAX_GRAPH_NODES // 2,)
        ).fetchall()
        for r in rows:
            bill_nid = f"bill_{r['billingDocument']}"
            so_nid   = f"so_{r['referenceSdDocument']}"
            if G.has_node(bill_nid) and G.has_node(so_nid):
                G.add_edge(so_nid, bill_nid, rel="HAS_INVOICE")

    # ── Journal Entries ───────────────────────────────────────────
    if table_exists("journal_entry_items_accounts_receivable"):
        rows = con.execute(
            """SELECT DISTINCT accountingDocument, referenceDocument, companyCode,
               postingDate, amountInTransactionCurrency, transactionCurrency,
               amountInCompanyCodeCurrency, companyCodeCurrency, customer
               FROM journal_entry_items_accounts_receivable LIMIT ?""",
            (MAX_GRAPH_NODES // 4,)
        ).fetchall()
        seen = set()
        for r in rows:
            doc = r["accountingDocument"]
            ref = r["referenceDocument"]
            if not doc:
                continue
            nid = f"je_{doc}"
            if nid not in seen:
                seen.add(nid)
                G.add_node(nid,
                    type="JournalEntry",
                    label=str(doc),
                    AccountingDocument=doc,
                    CompanyCode=r["companyCode"],
                    PostingDate=r["postingDate"],
                    Amount=r["amountInTransactionCurrency"],
                    Currency=r["transactionCurrency"],
                    Customer=r["customer"],
                )
            if ref:
                bill_nid = f"bill_{ref}"
                if G.has_node(bill_nid) and G.has_node(nid):
                    G.add_edge(bill_nid, nid, rel="HAS_JOURNAL_ENTRY")

    # ── Payments ──────────────────────────────────────────────────
    if table_exists("payments_accounts_receivable"):
        rows = con.execute(
            """SELECT DISTINCT accountingDocument, postingDate,
               amountInTransactionCurrency, transactionCurrency,
               companyCode, customer, clearingAccountingDocument
               FROM payments_accounts_receivable LIMIT ?""",
            (MAX_GRAPH_NODES // 4,)
        ).fetchall()
        for r in rows:
            doc = r["accountingDocument"]
            if not doc:
                continue
            nid = f"pay_{doc}"
            G.add_node(nid,
                type="Payment",
                label=str(doc),
                AccountingDocument=doc,
                PostingDate=r["postingDate"],
                Amount=r["amountInTransactionCurrency"],
                Currency=r["transactionCurrency"],
                CompanyCode=r["companyCode"],
                Customer=r["customer"],
            )
            je_nid = f"je_{doc}"
            if G.has_node(je_nid):
                G.add_edge(je_nid, nid, rel="HAS_PAYMENT")
            clearing = r["clearingAccountingDocument"]
            if clearing:
                je_clear = f"je_{clearing}"
                if G.has_node(je_clear) and not G.has_edge(je_clear, nid):
                    G.add_edge(je_clear, nid, rel="CLEARS")

    # ── Business Partners ─────────────────────────────────────────
    if table_exists("business_partners"):
        rows = con.execute(
            """SELECT businessPartner, businessPartnerFullName, businessPartnerName,
               organizationBpName1, businessPartnerCategory, industry
               FROM business_partners LIMIT 500"""
        ).fetchall()
        for r in rows:
            bp = r["businessPartner"]
            if not bp:
                continue
            name = (r["businessPartnerFullName"] or
                    r["organizationBpName1"] or
                    r["businessPartnerName"] or bp)
            nid = f"bp_{bp}"
            G.add_node(nid,
                type="BusinessPartner",
                label=str(name),
                BusinessPartner=bp,
                FullName=name,
                Category=r["businessPartnerCategory"],
                Industry=r["industry"],
            )

    # ── Link business partners → sales orders ─────────────────────
    for node_id, data in list(G.nodes(data=True)):
        if data.get("type") == "SalesOrder" and data.get("SoldToParty"):
            bp_nid = f"bp_{data['SoldToParty']}"
            if G.has_node(bp_nid):
                G.add_edge(bp_nid, node_id, rel="PLACED_ORDER")

    # ── Plants ────────────────────────────────────────────────────
    if table_exists("plants"):
        rows = con.execute(
            """SELECT plant, plantName, salesOrganization,
               distributionChannel, factoryCalendar
               FROM plants LIMIT 200"""
        ).fetchall()
        for r in rows:
            plant = r["plant"]
            if not plant:
                continue
            nid = f"plant_{plant}"
            G.add_node(nid,
                type="Plant",
                label=r["plantName"] or str(plant),
                Plant=plant,
                PlantName=r["plantName"],
                SalesOrganization=r["salesOrganization"],
            )

    # ── Products ──────────────────────────────────────────────────
    if table_exists("products"):
        rows = con.execute(
            """SELECT product, productType, productGroup,
               baseUnit, grossWeight, netWeight, weightUnit
               FROM products LIMIT 500"""
        ).fetchall()
        for r in rows:
            mat = r["product"]
            if not mat:
                continue
            nid = f"mat_{mat}"
            G.add_node(nid,
                type="Product",
                label=str(mat),
                Material=mat,
                ProductType=r["productType"],
                ProductGroup=r["productGroup"],
                BaseUnit=r["baseUnit"],
            )

    # ── Link products → sales order items ─────────────────────────
    for node_id, data in list(G.nodes(data=True)):
        if data.get("type") == "SalesOrderItem" and data.get("Material"):
            mat_nid = f"mat_{data['Material']}"
            if G.has_node(mat_nid):
                G.add_edge(mat_nid, node_id, rel="ORDERED_IN")

    con.close()
    print(f"  Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


# ── Serialisation ─────────────────────────────────────────────────────────────

def graph_to_json(G: nx.DiGraph) -> dict:
    nodes = []
    for nid, data in G.nodes(data=True):
        node = {"id": nid}
        node.update({k: v for k, v in data.items()
                     if v is not None and k not in ("__color",)})
        nodes.append(node)
    links = []
    for src, tgt, data in G.edges(data=True):
        links.append({"source": src, "target": tgt, "rel": data.get("rel", "")})
    return {"nodes": nodes, "links": links}


def save_graph_cache(G: nx.DiGraph) -> None:
    data = graph_to_json(G)
    with open(GRAPH_CACHE, "w") as f:
        json.dump(data, f)
    print(f"  Cached: {len(data['nodes'])} nodes, {len(data['links'])} edges → {GRAPH_CACHE}")


def load_graph_cache() -> dict | None:
    if os.path.exists(GRAPH_CACHE):
        with open(GRAPH_CACHE) as f:
            return json.load(f)
    return None