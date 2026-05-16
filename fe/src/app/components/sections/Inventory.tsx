import { useMemo, useState } from "react";
import { Card, CardContent } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Badge } from "../ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Textarea } from "../ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Warehouse, Plus, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { adminApi, text, type AdminSnapshot } from "../../api";

interface Props {
  data: AdminSnapshot | null;
  adminKey: string;
  refresh: () => Promise<void>;
}

export function Inventory({ data, adminKey, refresh }: Props) {
  const [addCode, setAddCode] = useState("");
  const [addData, setAddData] = useState("");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [filterCode, setFilterCode] = useState("ALL");
  const [releaseOrderId, setReleaseOrderId] = useState("");
  const [busy, setBusy] = useState(false);

  const pool = data?.pool || [];
  const productCodes = useMemo(
    () => {
      const fromProducts = (data?.products || []).map((p) => text(p.stock_code));
      const fromPool = (data?.pool || []).map((p) => text(p.stock_code));
      return Array.from(new Set([...fromProducts, ...fromPool].filter((x) => x !== "—"))).sort();
    },
    [data],
  );
  const counts = {
    READY: pool.filter((i) => text(i.status).toUpperCase() === "READY").length,
    HELD: pool.filter((i) => text(i.status).toUpperCase() === "HELD").length,
    SOLD: pool.filter((i) => text(i.status).toUpperCase() === "SOLD").length,
  };

  const visible = pool.filter((p) => {
    if (filterStatus !== "ALL" && text(p.status).toUpperCase() !== filterStatus) return false;
    if (filterCode !== "ALL" && text(p.stock_code) !== filterCode) return false;
    return true;
  });

  const addStock = async () => {
    setBusy(true);
    try {
      await adminApi("/admin/api/stock", adminKey, { method: "POST", body: JSON.stringify({ stock_code: addCode, items: addData }) });
      setAddData("");
      toast.success("Đã thêm stock vào kho");
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const releaseHeld = async () => {
    setBusy(true);
    try {
      const result = await adminApi<{ released: number }>("/admin/api/orders/release", adminKey, {
        method: "POST",
        body: JSON.stringify({ order_id: releaseOrderId, status: "EXPIRED" }),
      });
      setReleaseOrderId("");
      toast.success(`Đã trả ${result.released || 0} item về READY`);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const releaseHeldBulk = async (expiredOnly: boolean) => {
    if (!expiredOnly && !window.confirm("Trả toàn bộ HELD về READY? Chỉ dùng khi chắc chắn các đơn này không cần giữ nữa.")) return;
    setBusy(true);
    try {
      const result = await adminApi<{ released: number; orders: number }>("/admin/api/stock/release-held", adminKey, {
        method: "POST",
        body: JSON.stringify({ expired_only: expiredOnly, status: "EXPIRED" }),
      });
      toast.success(`Đã trả ${result.released || 0} item từ ${result.orders || 0} đơn về READY`);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="flex items-center gap-2"><Warehouse size={20} /> Kho hàng</h2>

      <div className="grid grid-cols-3 gap-3">
        {(["READY", "HELD", "SOLD"] as const).map((s) => (
          <Card key={s} className="shadow-sm">
            <CardContent className="p-4 flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{s}</span>
              <Badge variant={s === "READY" ? "default" : s === "HELD" ? "secondary" : "outline"} className="text-base px-3">{counts[s]}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="view">
        <TabsList>
          <TabsTrigger value="view">Xem kho</TabsTrigger>
          <TabsTrigger value="add">Thêm stock</TabsTrigger>
          <TabsTrigger value="release">Trả HELD</TabsTrigger>
        </TabsList>

        <TabsContent value="view" className="space-y-3 pt-2">
          <div className="flex flex-wrap gap-2">
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Tất cả</SelectItem>
                <SelectItem value="READY">READY</SelectItem>
                <SelectItem value="HELD">HELD</SelectItem>
                <SelectItem value="SOLD">SOLD</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterCode} onValueChange={setFilterCode}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Tất cả code</SelectItem>
                {productCodes.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <Card className="shadow-sm">
            <CardContent className="p-0 overflow-x-auto">
              <Table className="min-w-[920px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Item ID</TableHead>
                    <TableHead>Stock Code</TableHead>
                    <TableHead>Secret</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead>Hold Order</TableHead>
                    <TableHead>Hết hạn giữ</TableHead>
                    <TableHead>Sold Order</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visible.map((item) => (
                    <TableRow key={text(item.item_id)}>
                      <TableCell><code className="text-xs bg-muted px-1.5 py-0.5 rounded">{text(item.item_id)}</code></TableCell>
                      <TableCell><code className="text-xs bg-muted px-1.5 py-0.5 rounded">{text(item.stock_code)}</code></TableCell>
                      <TableCell className="text-xs font-mono max-w-[260px] truncate">{text(item.secret)}</TableCell>
                      <TableCell className="text-center"><StockBadge status={text(item.status)} /></TableCell>
                      <TableCell className="text-xs text-muted-foreground">{text(item.hold_order_id)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{text(item.hold_expires_at)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{text(item.sold_order_id)}</TableCell>
                    </TableRow>
                  ))}
                  {visible.length === 0 && <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground py-8">Không có stock nào</TableCell></TableRow>}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="add" className="space-y-3 pt-2">
          <Card className="shadow-sm max-w-2xl">
            <CardContent className="p-4 space-y-3">
              <Input placeholder="Stock code, ví dụ GPT1M" value={addCode} onChange={(e) => setAddCode(e.target.value.toUpperCase())} />
              <Textarea placeholder="Mỗi dòng là 1 account/secret" value={addData} onChange={(e) => setAddData(e.target.value)} />
              <Button className="gap-2" onClick={addStock} disabled={busy || !addCode || !addData.trim()}><Plus size={15} /> Thêm vào kho</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="release" className="space-y-3 pt-2">
          <Card className="shadow-sm max-w-2xl">
            <CardContent className="p-4 space-y-3">
              <p className="text-sm text-muted-foreground">
                Bình thường bot sẽ tự trả HELD về READY sau thời gian hết hạn. Nếu bị kẹt do restart/deploy, dùng nút bên dưới.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button className="gap-2" variant="outline" onClick={() => releaseHeldBulk(true)} disabled={busy}>
                  <RotateCcw size={15} /> Trả HELD quá hạn
                </Button>
                <Button className="gap-2" variant="destructive" onClick={() => releaseHeldBulk(false)} disabled={busy}>
                  <RotateCcw size={15} /> Trả toàn bộ HELD
                </Button>
              </div>
              <div className="border-t pt-3 space-y-2">
                <p className="text-sm text-muted-foreground">Hoặc nhập riêng Order ID đang HELD để trả các item của đơn về READY.</p>
                <Input placeholder="ORD..." value={releaseOrderId} onChange={(e) => setReleaseOrderId(e.target.value)} />
                <Button variant="outline" onClick={releaseHeld} disabled={busy || !releaseOrderId}>Trả Order ID này về READY</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StockBadge({ status }: { status: string }) {
  return <Badge variant={status === "READY" ? "default" : status === "HELD" ? "secondary" : "outline"}>{status}</Badge>;
}
