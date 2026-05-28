import { useState } from "react";
import { toast } from "sonner";
import { Loader2, Megaphone, Package, Pencil, Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Badge } from "../ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { Switch } from "../ui/switch";
import { adminApi, money, text, type AdminSnapshot, type AnyRow } from "../../api";

interface Props {
  data: AdminSnapshot | null;
  adminKey: string;
  refresh: () => Promise<void>;
}

const EMPTY = { product_id: "", name: "", stock_code: "", price: "", duration_days: "", expires_at: "", pricing_enabled: "true", description: "" };

const dateTimeLocal = (value: any) => {
  const raw = text(value);
  if (raw === "—" || raw === "â€”") return "";
  return raw.replace(" ", "T").slice(0, 16);
};

const isPricingEnabled = (value: any) => {
  const raw = String(value ?? "").trim().toLowerCase();
  return !["false", "0", "off", "no"].includes(raw);
};

export function Products({ data, adminKey, refresh }: Props) {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ ...EMPTY });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [broadcasting, setBroadcasting] = useState(false);

  const openAdd = () => {
    setForm({ ...EMPTY });
    setModalOpen(true);
  };

  const openEdit = (p: AnyRow) => {
    setForm({
      product_id: text(p.product_id) === "—" ? "" : text(p.product_id),
      name: text(p.name) === "—" ? "" : text(p.name),
      stock_code: text(p.stock_code) === "—" ? "" : text(p.stock_code),
      price: String(p.base_price || p.price || ""),
      duration_days: text(p.duration_days) === "—" ? "" : text(p.duration_days),
      expires_at: dateTimeLocal(p.expires_at),
      pricing_enabled: isPricingEnabled(p.pricing_enabled) ? "true" : "false",
      description: text(p.description) === "—" ? "" : text(p.description),
    });
    setModalOpen(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      await adminApi("/admin/api/products", adminKey, { method: "POST", body: JSON.stringify(form) });
      setModalOpen(false);
      await refresh();
    } finally {
      setSaving(false);
    }
  };

  const deleteCurrent = async () => {
    const productId = form.product_id.trim();
    if (!productId) return;
    const ok = window.confirm(`Xóa sản phẩm ${form.name || productId}? Sản phẩm sẽ biến mất khỏi menu bot.`);
    if (!ok) return;
    setDeleting(true);
    try {
      await adminApi(`/admin/api/products/${encodeURIComponent(productId)}`, adminKey, { method: "DELETE" });
      toast.success("Đã xóa sản phẩm");
      setModalOpen(false);
      await refresh();
    } finally {
      setDeleting(false);
    }
  };

  const notifyUsers = async () => {
    setBroadcasting(true);
    try {
      const result = await adminApi<{ sent?: number; failed?: number; total?: number }>(
        "/admin/api/products/broadcast-stock",
        adminKey,
        { method: "POST" },
      );
      toast.success(`Đã gửi thông báo kho: ${result.sent || 0}/${result.total || 0} user`);
      if (result.failed) toast.warning(`Có ${result.failed} user gửi lỗi`);
    } finally {
      setBroadcasting(false);
    }
  };

  const products = data?.products || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2"><Package size={20} /> Sản phẩm</h2>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" className="gap-1.5" onClick={notifyUsers} disabled={broadcasting}>
            {broadcasting ? <Loader2 size={15} className="animate-spin" /> : <Megaphone size={15} />}
            Thông báo user
          </Button>
          <Button size="sm" className="gap-1.5" onClick={openAdd}><Plus size={15} /> Thêm sản phẩm</Button>
        </div>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[940px]">
            <TableHeader>
              <TableRow>
                <TableHead>Tên sản phẩm</TableHead>
                <TableHead>Stock Code</TableHead>
                <TableHead className="text-right">Giá hiện tại</TableHead>
                <TableHead className="text-right">Giá gốc</TableHead>
                <TableHead className="text-center">Còn ngày</TableHead>
                <TableHead className="text-center">Auto date</TableHead>
                <TableHead className="text-center">READY</TableHead>
                <TableHead className="text-center">HELD</TableHead>
                <TableHead className="text-center">SOLD</TableHead>
                <TableHead>Mô tả</TableHead>
                <TableHead className="text-center">Sửa</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((p) => (
                <TableRow key={p.product_id || p.stock_code}>
                  <TableCell className="font-medium">{text(p.name)}</TableCell>
                  <TableCell><code className="bg-muted px-1.5 py-0.5 rounded text-xs">{text(p.stock_code)}</code></TableCell>
                  <TableCell className="text-right text-emerald-700">{money(p.price)}</TableCell>
                  <TableCell className="text-right">{money(p.base_price || p.price)}</TableCell>
                  <TableCell className="text-center">{p.is_time_priced ? text(p.remaining_days) : "—"}</TableCell>
                  <TableCell className="text-center"><Badge variant={isPricingEnabled(p.pricing_enabled) ? "secondary" : "outline"}>{isPricingEnabled(p.pricing_enabled) ? "Bật" : "Tắt"}</Badge></TableCell>
                  <TableCell className="text-center"><Badge variant={Number(p.READY) > 0 ? "default" : "destructive"}>{p.READY || 0}</Badge></TableCell>
                  <TableCell className="text-center"><Badge variant={Number(p.HELD) > 0 ? "secondary" : "outline"}>{p.HELD || 0}</Badge></TableCell>
                  <TableCell className="text-center"><Badge variant="outline">{p.SOLD || 0}</Badge></TableCell>
                  <TableCell className="text-sm text-muted-foreground max-w-[220px] truncate">{text(p.description)}</TableCell>
                  <TableCell className="text-center">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(p)}><Pencil size={14} /></Button>
                  </TableCell>
                </TableRow>
              ))}
              {products.length === 0 && <TableRow><TableCell colSpan={11} className="text-center text-muted-foreground py-8">Chưa có sản phẩm</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{form.product_id ? "Sửa sản phẩm" : "Thêm sản phẩm"}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1"><Label>Product ID</Label><Input value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} placeholder="Bỏ trống để tự tạo" /></div>
            <div className="space-y-1"><Label>Tên sản phẩm</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="space-y-1"><Label>Stock Code</Label><Input value={form.stock_code} onChange={(e) => setForm({ ...form, stock_code: e.target.value.toUpperCase() })} /></div>
            <div className="space-y-1"><Label>Giá gốc</Label><Input type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1"><Label>Tổng số ngày</Label><Input type="number" min="0" value={form.duration_days} onChange={(e) => setForm({ ...form, duration_days: e.target.value })} placeholder="Ví dụ: 7" /></div>
              <div className="space-y-1"><Label>Hết hạn lúc</Label><Input type="datetime-local" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} /></div>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-md border px-3 py-2">
              <Label htmlFor="pricing_enabled">Bật giá tự giảm theo date</Label>
              <Switch
                id="pricing_enabled"
                checked={form.pricing_enabled !== "false"}
                onCheckedChange={(checked) => setForm({ ...form, pricing_enabled: checked ? "true" : "false" })}
              />
            </div>
            <div className="space-y-1"><Label>Mô tả</Label><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <DialogFooter>
            {form.product_id && (
              <Button variant="destructive" className="mr-auto gap-1.5" onClick={deleteCurrent} disabled={deleting || saving}>
                <Trash2 size={15} />
                {deleting ? "Đang xóa..." : "Xóa"}
              </Button>
            )}
            <Button variant="outline" onClick={() => setModalOpen(false)}>Hủy</Button>
            <Button onClick={save} disabled={saving || deleting || !form.name || !form.stock_code}>{saving ? "Đang lưu..." : "Lưu"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
