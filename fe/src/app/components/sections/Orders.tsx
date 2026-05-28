import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, CalendarDays, ClipboardList, DollarSign, Plus, Search, ShoppingCart, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../ui/dialog";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { adminApi, money, text, type AdminSnapshot, type AnyRow } from "../../api";

type OrderStatus = "PENDING" | "PAID" | "DELIVERED" | "EXPIRED" | "CANCELLED";
type OrderFilter = OrderStatus | "ALL" | "FAILED";
type GptMark = { value: string; status?: string; note?: string };
type OrderView = "orders" | "revenue";
type RevenuePeriod = "day" | "custom" | "seven" | "week" | "month" | "year";

interface Props {
  data: AdminSnapshot | null;
  adminKey: string;
  refresh: () => Promise<void>;
  preset?: { status?: string; dateKey?: string; dateField?: "created_at" | "delivered_at"; view?: "revenue"; nonce: number };
  onBack?: () => void;
}

const ALL_STATUSES: OrderStatus[] = ["PENDING", "PAID", "DELIVERED", "EXPIRED", "CANCELLED"];

function materialKey(value: any) {
  const rawValue = String(value || "").trim();
  const firstPart = rawValue.split("|")[0]?.split("----")[0]?.trim() || rawValue;
  return firstPart.toLowerCase();
}

function dateKey(value: any) {
  const raw = String(value || "").trim();
  const hit = raw.match(/\d{4}-\d{2}-\d{2}/);
  return hit?.[0] || "";
}

function vnDay(offsetDays = 0) {
  const nowKey = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Ho_Chi_Minh" });
  const base = new Date(`${nowKey}T00:00:00+07:00`);
  base.setDate(base.getDate() + offsetDays);
  return base.toLocaleDateString("en-CA", { timeZone: "Asia/Ho_Chi_Minh" });
}

function parseVnDateKey(key: string) {
  if (!key) return null;
  const date = new Date(`${key}T00:00:00+07:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function periodRange(period: RevenuePeriod, selectedDateKey = "") {
  const todayKey = vnDay(0);
  const baseKey = period === "custom" && selectedDateKey ? selectedDateKey : todayKey;
  const start = parseVnDateKey(baseKey) || new Date();
  const end = new Date(start);
  end.setDate(end.getDate() + 1);

  if (period === "custom") {
    // Keep the one-day range from the chosen date.
  } else if (period === "seven") {
    start.setDate(start.getDate() - 6);
  } else if (period === "week") {
    const day = start.getDay() || 7;
    start.setDate(start.getDate() - day + 1);
  } else if (period === "month") {
    start.setDate(1);
  } else if (period === "year") {
    start.setMonth(0, 1);
  }

  return { start, end };
}

function isInPeriod(value: any, period: RevenuePeriod, selectedDateKey = "") {
  const key = dateKey(value);
  const date = parseVnDateKey(key);
  if (!date) return false;
  const { start, end } = periodRange(period, selectedDateKey);
  return date >= start && date < end;
}

function periodLabel(period: RevenuePeriod, selectedDateKey = "") {
  if (period === "day") return "hôm nay";
  if (period === "custom") return selectedDateKey || "ngày đã chọn";
  if (period === "seven") return "7 ngày gần nhất";
  if (period === "week") return "tuần này";
  if (period === "month") return "tháng này";
  return "năm nay";
}

function isSlotOrder(order: AnyRow) {
  return String(order.stock_code || "").trim().toUpperCase().startsWith("SLOT");
}

function slotEmail(order: AnyRow) {
  const raw = String(order.deliver_text || "");
  const match = raw.match(/slot_email\s*=\s*([^\s|,;]+)/i);
  return match?.[1] || "";
}

export function Orders({ data, adminKey, refresh, preset, onBack }: Props) {
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<OrderFilter>("ALL");
  const [filterDateKey, setFilterDateKey] = useState("");
  const [filterDateField, setFilterDateField] = useState<"created_at" | "delivered_at">("created_at");
  const [view, setView] = useState<OrderView>("orders");
  const [revenuePeriod, setRevenuePeriod] = useState<RevenuePeriod>("day");
  const [revenueDateKey, setRevenueDateKey] = useState(vnDay(0));
  const [expenseForm, setExpenseForm] = useState({ name: "", amount: "", date: vnDay(0), note: "" });
  const [changeModal, setChangeModal] = useState<{ open: boolean; order: AnyRow | null }>({ open: false, order: null });
  const [newStatus, setNewStatus] = useState<OrderStatus>("DELIVERED");
  const [busy, setBusy] = useState(false);
  const [dieKeys, setDieKeys] = useState<Set<string>>(new Set());

  const loadDieMaterials = useCallback(async () => {
    if (!adminKey) return;
    try {
      const response = await adminApi<{ items?: GptMark[] }>("/admin/api/gpt-marks", adminKey);
      const keys = new Set<string>();
      for (const item of response.items || []) {
        const status = String(item.status || "").toUpperCase();
        const note = String(item.note || "").toUpperCase();
        if (status !== "BANNED" && status !== "DIE" && !note.includes("OPENAI_DIE")) continue;
        const key = materialKey(item.value);
        if (key) keys.add(key);
      }
      setDieKeys(keys);
    } catch {
      // Keep the orders page usable when marks are temporarily unavailable.
    }
  }, [adminKey]);

  useEffect(() => {
    void loadDieMaterials();
  }, [loadDieMaterials]);

  useEffect(() => {
    if (!preset?.nonce) return;
    const status = (preset.status || "ALL").toUpperCase() as OrderFilter;
    setView(preset.view === "revenue" ? "revenue" : "orders");
    if (preset.view === "revenue") {
      setRevenuePeriod("day");
    }
    setFilterStatus(status === "FAILED" || ALL_STATUSES.includes(status as OrderStatus) ? status : "ALL");
    setFilterDateKey(preset.dateKey || "");
    setFilterDateField(preset.dateField || "created_at");
  }, [preset?.dateField, preset?.dateKey, preset?.nonce, preset?.status, preset?.view]);

  const usersById = useMemo(() => {
    const map = new Map<string, AnyRow>();
    for (const user of data?.users || []) {
      const id = text(user.chat_id || user.user_id);
      if (id !== "—") map.set(id, user);
    }
    return map;
  }, [data?.users]);

  const dieCountByOrder = useMemo(() => {
    const counts = new Map<string, number>();
    if (!dieKeys.size) return counts;

    for (const row of data?.pool || []) {
      const orderId = text(row.sold_order_id || row.hold_order_id);
      const key = materialKey(row.secret);
      if (orderId === "—" || !key || !dieKeys.has(key)) continue;
      counts.set(orderId, (counts.get(orderId) || 0) + 1);
    }

    for (const row of data?.deliveries || data?.fulfillments || []) {
      const orderId = text(row.order_id);
      const key = materialKey(row.secret);
      if (orderId === "—" || !key || !dieKeys.has(key)) continue;
      counts.set(orderId, (counts.get(orderId) || 0) + 1);
    }

    for (const order of data?.orders || []) {
      const orderId = text(order.order_id);
      const deliverText = String(order.deliver_text || "");
      if (orderId === "—" || !deliverText) continue;
      const dieLines = deliverText.split(/\r?\n/).filter((line) => dieKeys.has(materialKey(line)));
      if (dieLines.length) counts.set(orderId, Math.max(counts.get(orderId) || 0, dieLines.length));
    }
    return counts;
  }, [data?.deliveries, data?.fulfillments, data?.orders, data?.pool, dieKeys]);

  const orders = data?.orders || [];
  const todayKey = vnDay(0);
  const todayOrderCount = orders.filter((order) => dateKey(order.created_at) === todayKey).length;
  const todayRevenue = orders
    .filter((order) => text(order.status).toUpperCase() === "DELIVERED")
    .filter((order) => dateKey(order.delivered_at || order.paid_at || order.created_at) === todayKey)
    .reduce((sum, order) => sum + Number(order.total || 0), 0);
  const revenueOrders = orders.filter((order) => {
    if (text(order.status).toUpperCase() !== "DELIVERED") return false;
    return isInPeriod(order.delivered_at || order.paid_at || order.created_at, revenuePeriod, revenueDateKey);
  });
  const selectedRevenue = revenueOrders.reduce((sum, order) => sum + Number(order.total || 0), 0);
  const periodExpenses = (data?.expenses || []).filter((expense) => isInPeriod(expense.date || expense.created_at, revenuePeriod, revenueDateKey));
  const selectedExpense = periodExpenses.reduce((sum, expense) => sum + Number(expense.amount || 0), 0);
  const selectedProfit = selectedRevenue - selectedExpense;
  const expenseGroups = useMemo(() => {
    const map = new Map<string, { name: string; amount: number; count: number; notes: string[] }>();
    for (const expense of periodExpenses) {
      const name = text(expense.name) === "â€”" ? "Khác" : text(expense.name);
      const note = text(expense.note);
      const current = map.get(name) || { name, amount: 0, count: 0, notes: [] };
      current.amount += Number(expense.amount || 0);
      current.count += 1;
      if (note !== "â€”" && !current.notes.includes(note)) current.notes.push(note);
      map.set(name, current);
    }
    return Array.from(map.values()).sort((a, b) => b.amount - a.amount);
  }, [periodExpenses]);
  const maxExpenseGroup = Math.max(1, ...expenseGroups.map((item) => item.amount));
  const biggestExpense = expenseGroups[0];

  const visible = orders.filter((order) => {
    const status = text(order.status).toUpperCase();
    if (view === "revenue") {
      if (status !== "DELIVERED") return false;
      if (!isInPeriod(order.delivered_at || order.paid_at || order.created_at, revenuePeriod, revenueDateKey)) return false;
    } else if (filterStatus === "FAILED" && !["EXPIRED", "CANCELLED"].includes(status)) return false;
    if (filterStatus !== "ALL" && filterStatus !== "FAILED" && status !== filterStatus) return false;
    if (filterDateKey) {
      const dateValue = filterDateField === "delivered_at"
        ? order.delivered_at || order.paid_at || order.created_at
        : order.created_at;
      if (dateKey(dateValue) !== filterDateKey) return false;
    }
    const user = usersById.get(text(order.user_id));
    const hay = `${text(order.order_id)} ${text(order.user_id)} ${text(user?.username)} ${text(user?.full_name)} ${text(order.stock_code)} ${slotEmail(order)}`.toLowerCase();
    return !search || hay.includes(search.toLowerCase());
  });

  const openChange = (order: AnyRow) => {
    setNewStatus((text(order.status) === "—" ? "DELIVERED" : text(order.status)) as OrderStatus);
    setChangeModal({ open: true, order });
  };

  const applyChange = async () => {
    if (!changeModal.order) return;
    setBusy(true);
    try {
      await adminApi("/admin/api/orders/update", adminKey, {
        method: "POST",
        body: JSON.stringify({ order_id: changeModal.order.order_id, status: newStatus }),
      });
      setChangeModal({ open: false, order: null });
      await refresh();
      await loadDieMaterials();
    } finally {
      setBusy(false);
    }
  };

  const applyDayFilter = (key: string) => {
    setFilterDateKey(key);
    setFilterDateField("created_at");
  };

  const applyRevenueDate = (key: string) => {
    if (!key) return;
    setRevenueDateKey(key);
    setRevenuePeriod("custom");
  };

  const addExpense = async () => {
    const amount = Number(String(expenseForm.amount).replace(/[^\d]/g, ""));
    if (!expenseForm.name.trim()) return toast.warning("Nhập tên khoản chi trước nha");
    if (!amount) return toast.warning("Nhập số tiền lớn hơn 0");
    setBusy(true);
    try {
      await adminApi("/admin/api/expenses", adminKey, {
        method: "POST",
        body: JSON.stringify({ ...expenseForm, amount }),
      });
      setExpenseForm({ name: "", amount: "", date: vnDay(0), note: "" });
      await refresh();
      toast.success("Đã thêm chi phí");
    } finally {
      setBusy(false);
    }
  };

  const removeExpense = async (expenseId: string) => {
    if (!expenseId) return;
    setBusy(true);
    try {
      await adminApi(`/admin/api/expenses/${encodeURIComponent(expenseId)}`, adminKey, { method: "DELETE" });
      await refresh();
      toast.success("Đã xóa chi phí");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2">
          {view === "revenue" ? <DollarSign size={20} /> : <ClipboardList size={20} />}
          {view === "revenue" ? "Doanh thu" : "Đơn hàng"}
        </h2>
        {onBack && (
          <Button variant="outline" size="sm" className="gap-2" onClick={onBack}>
            <ArrowLeft size={15} /> Quay lại
          </Button>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Card className="shadow-sm">
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-xs text-muted-foreground">{view === "revenue" ? `Doanh thu ${periodLabel(revenuePeriod, revenueDateKey)}` : "Doanh thu hôm nay"}</p>
              <p className="mt-2 text-lg font-semibold text-emerald-700">{money(view === "revenue" ? selectedRevenue : todayRevenue)}</p>
              {view === "revenue" ? <p className="text-xs text-muted-foreground">{revenueOrders.length} đơn đã giao</p> : null}
            </div>
            <div className="rounded-md bg-emerald-50 p-2 text-emerald-600"><DollarSign size={20} /></div>
          </CardContent>
        </Card>
        <Card className="shadow-sm cursor-pointer transition hover:-translate-y-0.5 hover:shadow-md" onClick={() => applyDayFilter(todayKey)}>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-xs text-muted-foreground">Đơn hôm nay</p>
              <p className="mt-2 text-lg font-semibold text-blue-700">{todayOrderCount}</p>
            </div>
            <div className="rounded-md bg-blue-50 p-2 text-blue-600"><ShoppingCart size={20} /></div>
          </CardContent>
        </Card>
      </div>

      {view === "revenue" && (
        <>
          <div className="flex flex-wrap gap-2">
            {([
              ["day", "Hôm nay"],
              ["custom", revenueDateKey],
              ["seven", "7 ngày"],
              ["week", "Tuần"],
              ["month", "Tháng"],
              ["year", "Năm"],
            ] as [RevenuePeriod, string][]).map(([period, label]) => (
              <Button
                key={period}
                variant={revenuePeriod === period ? "default" : "outline"}
                size="sm"
                className="h-10"
                onClick={() => {
                  if (period === "custom") {
                    setRevenueDateKey(revenueDateKey || todayKey);
                  }
                  setRevenuePeriod(period);
                }}
              >
                {period === "custom" ? <CalendarDays size={15} /> : null}
                {label}
              </Button>
            ))}
            <div className="relative">
              <CalendarDays size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="date"
                value={revenueDateKey}
                onChange={(event) => applyRevenueDate(event.target.value)}
                className="h-10 w-[170px] pl-9 font-medium"
              />
            </div>
            <Button
              variant="secondary"
              size="sm"
              className="h-10"
              onClick={() => {
                setView("orders");
                setFilterStatus("ALL");
                setFilterDateKey("");
              }}
            >
              Xem tất cả đơn
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Card className="shadow-sm">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Chi phí {periodLabel(revenuePeriod, revenueDateKey)}</p>
                <p className="mt-2 text-lg font-semibold text-red-600">{money(selectedExpense)}</p>
                <p className="text-xs text-muted-foreground">{periodExpenses.length} khoản chi</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Lợi nhuận {periodLabel(revenuePeriod, revenueDateKey)}</p>
                <p className={`mt-2 text-lg font-semibold ${selectedProfit >= 0 ? "text-emerald-700" : "text-red-600"}`}>{money(selectedProfit)}</p>
                <p className="text-xs text-muted-foreground">Doanh thu - chi phí</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Chi nhiều nhất</p>
                <p className="mt-2 truncate text-lg font-semibold text-slate-900">{biggestExpense?.name || "Chưa có"}</p>
                <p className="text-xs text-muted-foreground">{biggestExpense ? money(biggestExpense.amount) : "0đ"}</p>
              </CardContent>
            </Card>
          </div>

          <Card className="shadow-sm">
            <CardContent className="space-y-4 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="font-semibold">Phân tích chi phí</h3>
                  <p className="text-xs text-muted-foreground">Gom theo tên khoản chi bạn nhập để biết tiền đang đi vào đâu.</p>
                </div>
                <Badge variant="outline">{expenseGroups.length} mục</Badge>
              </div>

              {expenseGroups.length ? (
                <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
                  <div className="space-y-3">
                    {expenseGroups.slice(0, 8).map((group) => {
                      const percent = Math.max(4, Math.round((group.amount / maxExpenseGroup) * 100));
                      return (
                        <div key={group.name} className="space-y-1">
                          <div className="flex items-center justify-between gap-2 text-sm">
                            <span className="truncate font-medium">{group.name}</span>
                            <span className="whitespace-nowrap text-red-600">{money(group.amount)}</span>
                          </div>
                          <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full rounded-full bg-red-500" style={{ width: `${percent}%` }} />
                          </div>
                          <p className="text-[11px] text-muted-foreground">{group.count} khoản chi</p>
                        </div>
                      );
                    })}
                  </div>

                  <div className="overflow-x-auto">
                    <Table className="min-w-[520px]">
                      <TableHeader>
                        <TableRow>
                          <TableHead>Mục chi</TableHead>
                          <TableHead className="text-center">Lần</TableHead>
                          <TableHead>Ghi chú</TableHead>
                          <TableHead className="text-right">Tổng</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {expenseGroups.map((group) => (
                          <TableRow key={group.name}>
                            <TableCell className="font-medium">{group.name}</TableCell>
                            <TableCell className="text-center">{group.count}</TableCell>
                            <TableCell className="max-w-[260px] truncate text-muted-foreground">{group.notes.slice(0, 2).join(" / ") || "—"}</TableCell>
                            <TableCell className="text-right text-red-600">{money(group.amount)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              ) : (
                <div className="rounded-md border border-dashed py-8 text-center text-sm text-muted-foreground">
                  Chưa có chi phí trong kỳ này. Nhập khoản chi ở form bên dưới để xem biểu đồ.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardContent className="space-y-3 p-4">
              <div className="grid gap-3 md:grid-cols-[1.3fr_0.8fr_0.8fr_1.2fr_auto]">
                <div className="space-y-1">
                  <Label>Tên khoản chi</Label>
                  <Input value={expenseForm.name} onChange={(e) => setExpenseForm({ ...expenseForm, name: e.target.value })} placeholder="Mua acc, mua mail, phí tool..." />
                </div>
                <div className="space-y-1">
                  <Label>Số tiền</Label>
                  <Input value={expenseForm.amount} onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })} placeholder="500000" inputMode="numeric" />
                </div>
                <div className="space-y-1">
                  <Label>Ngày</Label>
                  <Input type="date" value={expenseForm.date} onChange={(e) => setExpenseForm({ ...expenseForm, date: e.target.value })} />
                </div>
                <div className="space-y-1">
                  <Label>Ghi chú</Label>
                  <Input value={expenseForm.note} onChange={(e) => setExpenseForm({ ...expenseForm, note: e.target.value })} placeholder="Lô hàng / số lượng..." />
                </div>
                <div className="flex items-end">
                  <Button className="h-10 gap-1.5" onClick={addExpense} disabled={busy}>
                    <Plus size={15} /> Thêm
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      <div className="flex flex-wrap gap-2">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input className="pl-8 w-64" placeholder="Order ID / User / Code" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        {view !== "revenue" && (
          <>
            <Select value={filterStatus} onValueChange={(value) => setFilterStatus(value as OrderFilter)}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Tất cả</SelectItem>
                <SelectItem value="FAILED">Lỗi / hủy</SelectItem>
                {ALL_STATUSES.map((status) => <SelectItem key={status} value={status}>{status}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button
              variant={filterDateKey === todayKey && filterDateField === "created_at" ? "default" : "outline"}
              size="sm"
              className="h-10"
              onClick={() => applyDayFilter(todayKey)}
            >
              Hôm nay: {todayOrderCount}
            </Button>
            {filterDateKey && (
              <Button variant="secondary" size="sm" className="h-10 gap-2" onClick={() => setFilterDateKey("")}>
                {filterDateField === "delivered_at" ? "Giao ngày" : "Tạo ngày"} {filterDateKey}
                <span className="text-muted-foreground">×</span>
              </Button>
            )}
          </>
        )}
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[1180px]">
            <TableHeader>
              <TableRow>
                <TableHead>Order ID</TableHead>
                <TableHead>Khách</TableHead>
                <TableHead>Stock Code</TableHead>
                <TableHead>Email slot</TableHead>
                <TableHead className="text-center">SL</TableHead>
                <TableHead className="text-right">Tổng tiền</TableHead>
                <TableHead className="text-center">Trạng thái</TableHead>
                <TableHead>Tạo lúc</TableHead>
                <TableHead>Thanh toán</TableHead>
                <TableHead>Giao hàng</TableHead>
                <TableHead className="text-center">Sửa</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((order) => {
                const orderId = text(order.order_id);
                const user = usersById.get(text(order.user_id));
                const username = text(user?.username);
                const dieCount = dieCountByOrder.get(orderId) || 0;
                const email = slotEmail(order);
                return (
                  <TableRow key={orderId} id={`order-${orderId}`} className={dieCount ? "transition-colors bg-red-50/70 hover:bg-red-50" : "transition-colors"}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <code className="w-fit text-xs bg-muted px-1.5 py-0.5 rounded">{orderId}</code>
                        {dieCount > 0 && <Badge variant="destructive" className="w-fit">Die {dieCount}</Badge>}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      <div className="max-w-[160px]">
                        <div className="truncate font-medium text-foreground">{username !== "—" ? `@${username.replace(/^@/, "")}` : text(user?.full_name)}</div>
                        <div className="truncate font-mono text-xs">{text(order.user_id)}</div>
                      </div>
                    </TableCell>
                    <TableCell><code className="text-xs bg-muted px-1.5 py-0.5 rounded">{text(order.stock_code)}</code></TableCell>
                    <TableCell className="text-xs">
                      {isSlotOrder(order) ? (
                        email ? <span className="font-medium text-blue-700">{email}</span> : <span className="text-muted-foreground">Chưa có email</span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">{text(order.qty)}</TableCell>
                    <TableCell className="text-right text-emerald-700">{money(order.total)}</TableCell>
                    <TableCell className="text-center"><OrderBadge status={text(order.status)} /></TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{text(order.created_at)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{text(order.paid_at)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{text(order.delivered_at)}</TableCell>
                    <TableCell className="text-center"><Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => openChange(order)}>Đổi</Button></TableCell>
                  </TableRow>
                );
              })}
              {visible.length === 0 && <TableRow><TableCell colSpan={11} className="text-center text-muted-foreground py-8">Không có đơn hàng nào</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {view === "revenue" && (
        <Card className="shadow-sm">
          <CardContent className="p-0 overflow-x-auto">
            <Table className="min-w-[760px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Ngày</TableHead>
                  <TableHead>Khoản chi</TableHead>
                  <TableHead>Ghi chú</TableHead>
                  <TableHead className="text-right">Số tiền</TableHead>
                  <TableHead className="text-center">Xóa</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {periodExpenses.map((expense) => (
                  <TableRow key={text(expense.id)}>
                    <TableCell className="whitespace-nowrap">{text(expense.date)}</TableCell>
                    <TableCell className="font-medium">{text(expense.name)}</TableCell>
                    <TableCell className="text-muted-foreground">{text(expense.note)}</TableCell>
                    <TableCell className="text-right text-red-600">{money(expense.amount)}</TableCell>
                    <TableCell className="text-center">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-700" onClick={() => removeExpense(text(expense.id))} disabled={busy}>
                        <Trash2 size={14} />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {!periodExpenses.length && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">Chưa có khoản chi trong kỳ này</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog open={changeModal.open} onOpenChange={(open) => setChangeModal({ open, order: null })}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Đổi trạng thái đơn</DialogTitle></DialogHeader>
          {changeModal.order && (
            <div className="space-y-3 py-2">
              <p className="text-sm text-muted-foreground">Order: <strong>{text(changeModal.order.order_id)}</strong></p>
              <Select value={newStatus} onValueChange={(value) => setNewStatus(value as OrderStatus)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{ALL_STATUSES.map((status) => <SelectItem key={status} value={status}>{status}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setChangeModal({ open: false, order: null })}>Hủy</Button>
            <Button onClick={applyChange} disabled={busy}>Xác nhận</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function OrderBadge({ status }: { status: string }) {
  const bad = status === "EXPIRED" || status === "CANCELLED";
  const good = status === "DELIVERED" || status === "PAID";
  return <Badge variant={bad ? "destructive" : good ? "default" : "secondary"}>{status}</Badge>;
}
