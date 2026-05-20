import { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Badge } from "../ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Textarea } from "../ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Warehouse, Plus, RotateCcw, Copy } from "lucide-react";
import { toast } from "sonner";
import { adminApi, text, type AdminSnapshot } from "../../api";

interface Props {
  data: AdminSnapshot | null;
  adminKey: string;
  refresh: () => Promise<void>;
  preset?: { status?: string; stockCode?: string; nonce: number };
}

type MaterialItem = { value: string; status?: string; note?: string };

const normalizeCode = (value: any) => text(value).trim().toUpperCase();
const isRealCode = (value: string) => value !== "—" && value !== "â€”";
const stockItemKey = (value: any) => {
  const rawValue = String(value || "").trim();
  const firstPart = rawValue.split("|")[0]?.split("----")[0]?.trim() || rawValue;
  return firstPart.toLowerCase();
};
const countLines = (value: string) => value.split(/\r?\n/).filter((line) => line.trim()).length;

export function Inventory({ data, adminKey, refresh, preset }: Props) {
  const [addCode, setAddCode] = useState("");
  const [addData, setAddData] = useState("");
  const [duplicateData, setDuplicateData] = useState("");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [filterCode, setFilterCode] = useState("ALL");
  const [releaseOrderId, setReleaseOrderId] = useState("");
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
        const key = stockItemKey(item.value);
        if (key) keys.add(key);
      }
      setDieKeys(keys);
    } catch {
      // Keep inventory usable when materials are temporarily unavailable.
    }
  }, [adminKey]);

  useEffect(() => {
    void loadDieMaterials();
  }, [loadDieMaterials]);

  const pool = data?.pool || [];
  const productCodes = useMemo(
    () => {
      const fromProducts = (data?.products || []).map((p) => normalizeCode(p.stock_code));
      const fromPool = (data?.pool || []).map((p) => normalizeCode(p.stock_code));
      return Array.from(new Set([...fromProducts, ...fromPool].filter(isRealCode))).sort();
    },
    [data],
  );
  const counts = {
    READY: pool.filter((i) => text(i.status).toUpperCase() === "READY").length,
    HELD: pool.filter((i) => text(i.status).toUpperCase() === "HELD").length,
    SOLD: pool.filter((i) => text(i.status).toUpperCase() === "SOLD").length,
  };
  const dieCount = pool.filter((i) => dieKeys.has(stockItemKey(i.secret))).length;
  const addLineCount = countLines(addData);
  const duplicateLineCount = countLines(duplicateData);

  const visible = pool.filter((p) => {
    if (filterStatus !== "ALL" && text(p.status).toUpperCase() !== filterStatus) return false;
    if (filterCode !== "ALL" && normalizeCode(p.stock_code) !== normalizeCode(filterCode)) return false;
    return true;
  });

  useEffect(() => {
    if (!preset?.nonce) return;
    const status = (preset.status || "ALL").toUpperCase();
    setFilterStatus(["ALL", "READY", "HELD", "SOLD"].includes(status) ? status : "ALL");
    setFilterCode(preset.stockCode ? normalizeCode(preset.stockCode) : "ALL");
    if (preset.stockCode) setAddCode(normalizeCode(preset.stockCode));
  }, [preset?.nonce, preset?.status, preset?.stockCode]);

  const addStock = async () => {
    const lines = addData.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length) return;
    const stockKeys = new Set((data?.pool || []).map((row) => stockItemKey(row.secret)).filter(Boolean));
    const seenKeys = new Set<string>();
    const cleanLines: string[] = [];
    const duplicateLines: string[] = [];

    lines.forEach((line) => {
      const key = stockItemKey(line);
      if (stockKeys.has(key) || seenKeys.has(key)) {
        duplicateLines.push(line);
        return;
      }
      seenKeys.add(key);
      cleanLines.push(line);
    });

    if (!cleanLines.length) {
      setAddData("");
      setDuplicateData(duplicateLines.join("\n"));
      toast.warning(`Không thêm dòng nào. Đã lọc ${duplicateLines.length} dòng trùng.`);
      return;
    }

    setBusy(true);
    try {
      const result = await adminApi<{ added: number; skipped_duplicates?: string[] }>("/admin/api/stock", adminKey, {
        method: "POST",
        body: JSON.stringify({ stock_code: addCode, items: cleanLines.join("\n") }),
      });
      const duplicates = [...duplicateLines, ...(result.skipped_duplicates || [])];
      setAddData("");
      setDuplicateData(duplicates.join("\n"));
      const duplicateMessage = duplicates.length ? `, lọc trùng ${duplicates.length} dòng` : "";
      toast.success(`Đã thêm ${result.added ?? cleanLines.length} dòng vào kho${duplicateMessage}`);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const copyDuplicateData = async () => {
    if (!duplicateData.trim()) return toast.info("Không có dòng trùng để copy");
    await navigator.clipboard.writeText(duplicateData);
    toast.success("Đã copy dòng trùng");
  };

  const copyStockSecret = async (value: string) => {
    if (!value || value === "—") return toast.info("Không có dữ liệu để copy");
    await navigator.clipboard.writeText(value);
    toast.success("Đã copy stock");
  };

  const updateStockStatus = async (itemId: string, status: "READY" | "SOLD") => {
    if (!itemId || itemId === "—") return toast.warning("Item này thiếu item_id");
    if (status === "READY" && !window.confirm("Trả item này về READY để bán lại?")) return;
    if (status === "SOLD" && !window.confirm("Đánh dấu item này là đã bán thủ công?")) return;
    setBusy(true);
    try {
      await adminApi("/admin/api/stock/update", adminKey, {
        method: "POST",
        body: JSON.stringify({ item_id: itemId, status, sold_order_id: "MANUAL" }),
      });
      toast.success(status === "READY" ? "Đã trả item về READY" : "Đã đánh dấu item là SOLD");
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

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
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
            <Badge variant="outline" className="h-9 px-3">
              Đang hiện {visible.length}/{pool.length}
            </Badge>
            <Badge variant="destructive" className="h-9 px-3">
              Die {dieCount}
            </Badge>
          </div>

          <Card className="shadow-sm">
            <CardContent className="p-0 overflow-x-auto">
              <Table className="min-w-[1040px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Item ID</TableHead>
                    <TableHead>Stock Code</TableHead>
                    <TableHead>Secret</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead>Hold Order</TableHead>
                    <TableHead>Hết hạn giữ</TableHead>
                    <TableHead>Sold Order</TableHead>
                    <TableHead className="text-right">Thao tác</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visible.map((item, index) => {
                    const itemId = text(item.item_id);
                    const secret = text(item.secret);
                    const status = text(item.status).toUpperCase();
                    const isDie = dieKeys.has(stockItemKey(secret));
                    return (
                      <TableRow
                        key={`${itemId}-${normalizeCode(item.stock_code)}-${index}-${secret.slice(0, 24)}`}
                        className={isDie ? "bg-red-50/70 hover:bg-red-50" : ""}
                      >
                        <TableCell><code className="text-xs bg-muted px-1.5 py-0.5 rounded">{itemId}</code></TableCell>
                        <TableCell><code className="text-xs bg-muted px-1.5 py-0.5 rounded">{text(item.stock_code)}</code></TableCell>
                        <TableCell
                          className="max-w-[260px] cursor-pointer select-none truncate font-mono text-xs active:bg-muted"
                          title="Chạm để copy"
                          onClick={() => copyStockSecret(secret)}
                        >
                          <span className="inline-flex min-w-0 max-w-full items-center gap-2">
                            <span className="truncate">{secret}</span>
                            {isDie && <Badge variant="destructive" className="shrink-0">Die</Badge>}
                          </span>
                        </TableCell>
                        <TableCell className="text-center"><StockBadge status={text(item.status)} /></TableCell>
                        <TableCell className="text-xs text-muted-foreground">{text(item.hold_order_id)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{text(item.hold_expires_at)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{text(item.sold_order_id)}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button size="sm" variant="outline" onClick={() => updateStockStatus(itemId, "SOLD")} disabled={busy || status === "SOLD"}>
                              Đã bán
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => updateStockStatus(itemId, "READY")} disabled={busy || status === "READY"}>
                              Bán lại
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {visible.length === 0 && <TableRow><TableCell colSpan={8} className="text-center text-muted-foreground py-8">Không có stock nào</TableCell></TableRow>}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="add" className="space-y-3 pt-2">
          <Card className="max-w-full shadow-sm lg:max-w-5xl">
            <CardContent className="p-4 space-y-3">
              <div className="grid min-w-0 gap-3 md:grid-cols-[260px_minmax(0,1fr)]">
                <div className="min-w-0 space-y-3">
                  <Select value={addCode || "__custom"} onValueChange={(value) => setAddCode(value === "__custom" ? "" : value)}>
                    <SelectTrigger><SelectValue placeholder="Chọn stock code có sẵn" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__custom">Nhập mã khác</SelectItem>
                      {productCodes.map((code) => <SelectItem key={code} value={code}>{code}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Input placeholder="Stock code, ví dụ GPT1M" value={addCode} onChange={(e) => setAddCode(e.target.value.toUpperCase())} />
                  <Button className="w-full gap-2" onClick={addStock} disabled={busy || !addCode || !addData.trim()}>
                    <Plus size={15} /> Thêm vào kho
                  </Button>
                </div>

                <div className="grid min-w-0 gap-3 lg:grid-cols-2">
                  <div className="min-w-0 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">Dán hàng vào</p>
                      <Badge variant="outline">{addLineCount} dòng</Badge>
                    </div>
                    <Textarea
                      className="h-40 min-h-40 min-w-0 max-w-full overflow-auto whitespace-pre font-mono text-xs [field-sizing:fixed]"
                      placeholder="Mỗi dòng là 1 account/secret"
                      value={addData}
                      wrap="off"
                      onChange={(e) => setAddData(e.target.value)}
                    />
                  </div>

                  <div className="min-w-0 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">Dòng trùng bị lọc</p>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge variant="outline">{duplicateLineCount} dòng</Badge>
                        <Button size="sm" variant="outline" className="h-8 gap-1" onClick={copyDuplicateData} disabled={!duplicateData.trim()}>
                          <Copy size={14} /> Copy
                        </Button>
                      </div>
                    </div>
                    <Textarea
                      className="h-40 min-h-40 min-w-0 max-w-full overflow-auto whitespace-pre font-mono text-xs [field-sizing:fixed]"
                      placeholder="Dòng trùng sẽ hiện ở đây sau khi thêm"
                      value={duplicateData}
                      wrap="off"
                      onChange={(e) => setDuplicateData(e.target.value)}
                    />
                  </div>
                </div>
              </div>
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
