import { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { Input } from "../ui/input";
import { ClipboardList, Search } from "lucide-react";
import { adminApi, money, text, type AdminSnapshot, type AnyRow } from "../../api";

type OrderStatus = "PENDING" | "PAID" | "DELIVERED" | "EXPIRED" | "CANCELLED";
type OrderFilter = OrderStatus | "ALL" | "FAILED";
type MaterialItem = { value: string; status?: string; note?: string };

interface Props {
  data: AdminSnapshot | null;
  adminKey: string;
  refresh: () => Promise<void>;
  preset?: { status?: string; nonce: number };
}

const ALL_STATUSES: OrderStatus[] = ["PENDING", "PAID", "DELIVERED", "EXPIRED", "CANCELLED"];

function materialKey(value: any) {
  const rawValue = String(value || "").trim();
  const firstPart = rawValue.split("|")[0]?.split("----")[0]?.trim() || rawValue;
  return firstPart.toLowerCase();
}

export function Orders({ data, adminKey, refresh, preset }: Props) {
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<OrderFilter>("ALL");
  const [changeModal, setChangeModal] = useState<{ open: boolean; order: AnyRow | null }>({ open: false, order: null });
  const [newStatus, setNewStatus] = useState<OrderStatus>("DELIVERED");
  const [busy, setBusy] = useState(false);
  const [dieKeys, setDieKeys] = useState<Set<string>>(new Set());

  const loadDieMaterials = useCallback(async () => {
    if (!adminKey) return;
    try {
      const response = await adminApi<{ items?: MaterialItem[] }>("/admin/api/materials", adminKey);
      const keys = new Set<string>();
      for (const item of response.items || []) {
        const status = String(item.status || "").toUpperCase();
        const note = String(item.note || "").toUpperCase();
        if (status !== "BAD" || !note.includes("OPENAI_DIE")) continue;
        const key = materialKey(item.value);
        if (key) keys.add(key);
      }
      setDieKeys(keys);
    } catch {
      // Keep the orders page usable when materials are temporarily unavailable.
    }
  }, [adminKey]);

  useEffect(() => {
    void loadDieMaterials();
  }, [loadDieMaterials]);

  useEffect(() => {
    if (!preset?.nonce) return;
    const status = (preset.status || "ALL").toUpperCase() as OrderFilter;
    setFilterStatus(status === "FAILED" || ALL_STATUSES.includes(status as OrderStatus) ? status : "ALL");
  }, [preset?.nonce, preset?.status]);

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
    for (const row of data?.deliveries || data?.fulfillments || []) {
      const orderId = text(row.order_id);
      const key = materialKey(row.secret);
      if (orderId === "—" || !key || !dieKeys.has(key)) continue;
      counts.set(orderId, (counts.get(orderId) || 0) + 1);
    }
    return counts;
  }, [data?.deliveries, data?.fulfillments, dieKeys]);

  const orders = data?.orders || [];
  const visible = orders.filter((order) => {
    const status = text(order.status).toUpperCase();
    if (filterStatus === "FAILED" && !["EXPIRED", "CANCELLED"].includes(status)) return false;
    if (filterStatus !== "ALL" && filterStatus !== "FAILED" && status !== filterStatus) return false;
    const user = usersById.get(text(order.user_id));
    const hay = `${text(order.order_id)} ${text(order.user_id)} ${text(user?.username)} ${text(user?.full_name)} ${text(order.stock_code)}`.toLowerCase();
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

  return (
    <div className="space-y-4">
      <h2 className="flex items-center gap-2"><ClipboardList size={20} /> Đơn hàng</h2>

      <div className="flex flex-wrap gap-2">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input className="pl-8 w-64" placeholder="Order ID / User / Code" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select value={filterStatus} onValueChange={(value) => setFilterStatus(value as OrderFilter)}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Tất cả</SelectItem>
            <SelectItem value="FAILED">Lỗi / hủy</SelectItem>
            {ALL_STATUSES.map((status) => <SelectItem key={status} value={status}>{status}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[1060px]">
            <TableHeader>
              <TableRow>
                <TableHead>Order ID</TableHead>
                <TableHead>Khách</TableHead>
                <TableHead>Stock Code</TableHead>
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
              {visible.length === 0 && <TableRow><TableCell colSpan={10} className="text-center text-muted-foreground py-8">Không có đơn hàng nào</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

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
