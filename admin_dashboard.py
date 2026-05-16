import asyncio
import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from admin_services import add_stock, release_order, save_product, snapshot, update_order


ADMIN_HTML = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bot Admin</title>
  <style>
    :root { color-scheme: dark; --bg:#101112; --panel:#191b1d; --line:#303338; --text:#f2f2f2; --muted:#aeb4bd; --accent:#4f9f68; --bad:#a74343; --warn:#9b7a2a; }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: Arial, sans-serif; }
    header { display:flex; gap:12px; align-items:center; justify-content:space-between; padding:14px 18px; background:#1d2023; border-bottom:1px solid var(--line); position:sticky; top:0; z-index:5; }
    h1 { font-size:20px; margin:0; }
    h2 { margin: 18px 0 10px; font-size:18px; }
    input, textarea, select, button { border:1px solid #444a50; border-radius:6px; padding:9px 10px; background:#111315; color:var(--text); font:inherit; }
    textarea { min-height:110px; width:100%; resize:vertical; }
    button { cursor:pointer; background:var(--accent); border-color:#61b87b; color:#fff; font-weight:700; }
    button.secondary { background:#2b3035; border-color:#464d54; }
    button.danger { background:var(--bad); border-color:#b95a5a; }
    main { padding:18px; max-width:1380px; margin:auto; }
    .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .tabs { display:flex; gap:8px; flex-wrap:wrap; margin: 14px 0; }
    .tab { background:#24282d; border-color:#3a4047; }
    .tab.active { background:#315b3d; border-color:#4f9f68; }
    .panel { display:none; }
    .panel.active { display:block; }
    .grid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:13px; min-height:74px; }
    .label { color:var(--muted); font-size:12px; text-transform:uppercase; }
    .value { font-size:22px; margin-top:8px; font-weight:700; }
    .form { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; margin-bottom:12px; }
    .form .wide { grid-column:span 2; }
    .form .full { grid-column:1/-1; }
    table { width:100%; border-collapse:collapse; background:#151719; }
    th, td { border-bottom:1px solid #2a2e33; padding:8px; text-align:left; font-size:13px; vertical-align:top; }
    th { position:sticky; top:0; background:#22262a; z-index:2; }
    .scroll { max-height:560px; overflow:auto; border:1px solid var(--line); border-radius:8px; }
    .pill { display:inline-block; padding:3px 7px; border-radius:999px; background:#343a40; white-space:nowrap; }
    .READY,.DELIVERED,.PAID { background:#1e6035; }
    .HELD,.PENDING { background:var(--warn); color:#fff; }
    .SOLD { background:#44516b; }
    .CANCELLED,.EXPIRED { background:var(--bad); }
    .muted { color:var(--muted); }
    .msg { margin:10px 0; color:#d7e8d9; }
    @media (max-width:900px){ .grid{grid-template-columns:repeat(2,minmax(0,1fr));}.form{grid-template-columns:1fr}.form .wide{grid-column:auto} header{align-items:stretch; flex-direction:column;} }
  </style>
</head>
<body>
  <header>
    <h1>Khoi Van Store Admin</h1>
    <div class="toolbar">
      <input id="key" placeholder="ADMIN_PASSWORD" type="password" />
      <button onclick="loadData()">Refresh</button>
    </div>
  </header>
  <main>
    <div id="message" class="msg">Nhap ADMIN_PASSWORD roi bam Refresh.</div>
    <div class="tabs">
      <button class="tab active" onclick="showTab('dashboard', this)">Dashboard</button>
      <button class="tab" onclick="showTab('products', this)">San pham</button>
      <button class="tab" onclick="showTab('stock', this)">Kho</button>
      <button class="tab" onclick="showTab('orders', this)">Don hang</button>
      <button class="tab" onclick="showTab('users', this)">Khach hang</button>
      <button class="tab" onclick="showTab('reservations', this)">Reservations</button>
    </div>

    <section id="dashboard" class="panel active">
      <div class="grid" id="summary"></div>
    </section>

    <section id="products" class="panel">
      <h2>Them / sua san pham</h2>
      <div class="form">
        <input id="p_product_id" placeholder="product_id (bo trong se tu tao)" />
        <input id="p_name" placeholder="Ten san pham" />
        <input id="p_stock_code" placeholder="stock_code" />
        <input id="p_price" placeholder="Gia" type="number" />
        <textarea class="full" id="p_description" placeholder="Mo ta"></textarea>
        <button onclick="saveProduct()">Luu san pham</button>
      </div>
      <div class="scroll"><table id="productsTable"></table></div>
    </section>

    <section id="stock" class="panel">
      <h2>Nhap stock/account</h2>
      <div class="form">
        <input id="s_stock_code" placeholder="stock_code" />
        <textarea class="full" id="s_items" placeholder="Moi dong la 1 account/secret"></textarea>
        <button onclick="addStockItems()">Them vao kho</button>
      </div>
      <div class="scroll"><table id="stockTable"></table></div>
    </section>

    <section id="orders" class="panel">
      <h2>Don hang</h2>
      <div class="form">
        <input id="o_order_id" placeholder="order_id" />
        <select id="o_status"><option value="EXPIRED">EXPIRED</option><option value="CANCELLED">CANCELLED</option><option value="PENDING">PENDING</option><option value="PAID">PAID</option><option value="DELIVERED">DELIVERED</option></select>
        <button onclick="releaseHeld()">Release HELD -> READY</button>
        <button class="secondary" onclick="setOrderStatus()">Doi status don</button>
      </div>
      <div class="scroll"><table id="ordersTable"></table></div>
    </section>

    <section id="users" class="panel">
      <h2>Khach hang da bam bot</h2>
      <div class="scroll"><table id="usersTable"></table></div>
    </section>

    <section id="reservations" class="panel">
      <h2>Reservations / Fulfillments</h2>
      <div class="scroll"><table id="reservationsTable"></table></div>
      <h2>Fulfillments</h2>
      <div class="scroll"><table id="fulfillmentsTable"></table></div>
    </section>
  </main>

<script>
let DATA = null;
const saved = localStorage.getItem("admin_key") || "";
document.getElementById("key").value = saved;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
const fmt = n => Number(n || 0).toLocaleString("vi-VN");
const key = () => document.getElementById("key").value.trim();
function msg(t){ document.getElementById("message").textContent = t; }
function showTab(id, btn){ document.querySelectorAll(".panel").forEach(x=>x.classList.remove("active")); document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active")); document.getElementById(id).classList.add("active"); btn.classList.add("active"); }
async function api(path, options={}){
  const sep = path.includes("?") ? "&" : "?";
  const res = await fetch(`${path}${sep}key=${encodeURIComponent(key())}`, {headers: {"content-type":"application/json"}, ...options});
  if(!res.ok) throw new Error(await res.text());
  return res.json();
}
async function loadData(){
  localStorage.setItem("admin_key", key());
  msg("Dang tai...");
  try {
    DATA = await api("/admin/api/snapshot?limit=150");
    render();
    msg(`Cap nhat: ${DATA.generated_at} (${DATA.timezone})`);
  } catch(e) { msg(e.message); }
}
function render(){
  const s = DATA.summary, c = s.status_counts || {};
  document.getElementById("summary").innerHTML = [
    ["Tong don", s.orders], ["Doanh thu", fmt(s.revenue)+" d"], ["Users", s.users],
    ["Ready", s.stock_ready], ["Held", s.stock_held], ["Sold", s.stock_sold],
    ["Pending", c.PENDING||0], ["Delivered", c.DELIVERED||0], ["Expired", c.EXPIRED||0], ["Cancelled", c.CANCELLED||0]
  ].map(([a,b])=>`<div class="card"><div class="label">${a}</div><div class="value">${b}</div></div>`).join("");
  document.getElementById("productsTable").innerHTML = `<tr><th>ID</th><th>Ten</th><th>Stock</th><th>Gia</th><th>READY</th><th>HELD</th><th>SOLD</th><th>Mo ta</th></tr>` +
    DATA.products.map(p=>`<tr onclick='fillProduct(${JSON.stringify(p).replaceAll("'","&#39;")})'><td>${esc(p.product_id)}</td><td>${esc(p.name)}</td><td>${esc(p.stock_code)}</td><td>${fmt(p.price)}</td><td>${p.READY||0}</td><td>${p.HELD||0}</td><td>${p.SOLD||0}</td><td>${esc(p.description)}</td></tr>`).join("");
  document.getElementById("stockTable").innerHTML = table(DATA.pool, ["item_id","stock_code","status","hold_order_id","hold_at","hold_expires_at","sold_order_id","sold_at"]);
  document.getElementById("ordersTable").innerHTML = table(DATA.orders, ["order_id","user_id","stock_code","qty","total","status","created_at","paid_at","tx_id","delivered_at"]);
  document.getElementById("usersTable").innerHTML = table(DATA.users, ["chat_id","username","full_name","orders","spent","updated_at"]);
  document.getElementById("reservationsTable").innerHTML = table(DATA.reservations, ["order_id","item_id","stock_code","reserved_at","expires_at","released_at","sold_at"]);
  document.getElementById("fulfillmentsTable").innerHTML = table(DATA.fulfillments, ["order_id","item_id","stock_code","delivered_at"]);
}
function table(rows, cols){
  return `<tr>${cols.map(c=>`<th>${c}</th>`).join("")}</tr>` + (rows||[]).map(r=>`<tr>${cols.map(c=>{
    const v = r[c] ?? "";
    return c === "status" ? `<td><span class="pill ${esc(v)}">${esc(v)}</span></td>` : `<td>${esc(v)}</td>`;
  }).join("")}</tr>`).join("");
}
function fillProduct(p){
  document.getElementById("p_product_id").value = p.product_id || "";
  document.getElementById("p_name").value = p.name || "";
  document.getElementById("p_stock_code").value = p.stock_code || "";
  document.getElementById("p_price").value = p.price || "";
  document.getElementById("p_description").value = p.description || "";
}
async function saveProduct(){
  try {
    await api("/admin/api/products", {method:"POST", body: JSON.stringify({
      product_id: document.getElementById("p_product_id").value,
      name: document.getElementById("p_name").value,
      stock_code: document.getElementById("p_stock_code").value,
      price: document.getElementById("p_price").value,
      description: document.getElementById("p_description").value,
    })});
    msg("Da luu san pham."); await loadData();
  } catch(e) { msg(e.message); }
}
async function addStockItems(){
  try {
    const r = await api("/admin/api/stock", {method:"POST", body: JSON.stringify({stock_code: document.getElementById("s_stock_code").value, items: document.getElementById("s_items").value})});
    msg(`Da them ${r.added} item.`); document.getElementById("s_items").value = ""; await loadData();
  } catch(e) { msg(e.message); }
}
async function releaseHeld(){
  try {
    const r = await api("/admin/api/orders/release", {method:"POST", body: JSON.stringify({order_id: document.getElementById("o_order_id").value, status: document.getElementById("o_status").value})});
    msg(`Da tra kho ${r.released} item.`); await loadData();
  } catch(e) { msg(e.message); }
}
async function setOrderStatus(){
  try {
    await api("/admin/api/orders/update", {method:"POST", body: JSON.stringify({order_id: document.getElementById("o_order_id").value, status: document.getElementById("o_status").value})});
    msg("Da doi status don."); await loadData();
  } catch(e) { msg(e.message); }
}
</script>
</body>
</html>"""


def require_admin(request: Request) -> None:
    expected = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Set ADMIN_PASSWORD in Render Environment first.")
    provided = (request.query_params.get("key") or request.headers.get("x-admin-key") or "").strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def register_admin_routes(app: FastAPI) -> None:
    @app.get("/admin", response_class=HTMLResponse)
    async def admin_page():
        return ADMIN_HTML

    @app.get("/admin/api/snapshot")
    async def admin_snapshot(request: Request, limit: int = 100):
        require_admin(request)
        return await asyncio.to_thread(snapshot, limit)

    @app.post("/admin/api/products")
    async def admin_save_product(request: Request):
        require_admin(request)
        return await asyncio.to_thread(save_product, await request.json())

    @app.post("/admin/api/stock")
    async def admin_add_stock(request: Request):
        require_admin(request)
        return await asyncio.to_thread(add_stock, await request.json())

    @app.post("/admin/api/orders/release")
    async def admin_release_order(request: Request):
        require_admin(request)
        data: Dict[str, Any] = await request.json()
        return await asyncio.to_thread(release_order, data.get("order_id", ""), data.get("status", "EXPIRED"))

    @app.post("/admin/api/orders/update")
    async def admin_update_order(request: Request):
        require_admin(request)
        data: Dict[str, Any] = await request.json()
        order_id = data.pop("order_id", "")
        return await asyncio.to_thread(update_order, order_id, data)
