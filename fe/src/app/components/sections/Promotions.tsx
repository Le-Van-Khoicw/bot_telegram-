import { useState } from "react";
import { Gift, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../ui/dialog";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Switch } from "../ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Textarea } from "../ui/textarea";
import { adminApi, money, text, type AdminSnapshot, type AnyRow } from "../../api";

interface Props {
  data: AdminSnapshot | null;
  adminKey: string;
  refresh: () => Promise<void>;
}

const EMPTY = { id: "", code: "", discount_amount: "20000", min_order_total: "50000", required_orders: "10", expires_days: "7", status: "ACTIVE", note: "" };

export function Promotions({ data, adminKey, refresh }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ ...EMPTY });
  const settings = data?.promo_settings || {};
  const [menuEnabled, setMenuEnabled] = useState(String(settings.menu_enabled || "").toUpperCase() === "TRUE");
  const [menuText, setMenuText] = useState(String(settings.menu_text || ""));
  const [saving, setSaving] = useState(false);

  const promotions = data?.promotions || [];
  const awards = data?.promo_awards || [];

  const syncSettings = () => {
    setMenuEnabled(String(settings.menu_enabled || "").toUpperCase() === "TRUE");
    setMenuText(String(settings.menu_text || ""));
  };

  const openAdd = () => {
    setForm({ ...EMPTY });
    setOpen(true);
  };

  const openEdit = (promo: AnyRow) => {
    setForm({
      id: text(promo.id) === "—" ? "" : text(promo.id),
      code: text(promo.code) === "—" ? "" : text(promo.code),
      discount_amount: text(promo.discount_amount || promo.discount_percent) === "—" ? "20000" : text(promo.discount_amount || promo.discount_percent),
      min_order_total: text(promo.min_order_total) === "—" ? "50000" : text(promo.min_order_total),
      required_orders: text(promo.required_orders) === "—" ? "10" : text(promo.required_orders),
      expires_days: text(promo.expires_days) === "—" ? "7" : text(promo.expires_days),
      status: text(promo.status) === "PAUSED" ? "PAUSED" : "ACTIVE",
      note: text(promo.note) === "—" ? "" : text(promo.note),
    });
    setOpen(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      await adminApi("/admin/api/promotions", adminKey, { method: "POST", body: JSON.stringify(form) });
      toast.success("Đã lưu khuyến mãi");
      setOpen(false);
      await refresh();
    } finally {
      setSaving(false);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      await adminApi("/admin/api/promo-settings", adminKey, {
        method: "POST",
        body: JSON.stringify({ menu_enabled: menuEnabled, menu_text: menuText }),
      });
      toast.success("Đã lưu thông báo menu");
      await refresh();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2"><Gift size={20} /> Khuyến mãi</h2>
        <Button size="sm" className="gap-1.5" onClick={openAdd}><Plus size={15} /> Thêm mã</Button>
      </div>

      <Card className="shadow-sm">
        <CardContent className="space-y-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">Thông báo khuyến mãi trong menu bot</h3>
              <p className="text-xs text-muted-foreground">Nội dung này sẽ hiện trong /shop khi bật.</p>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="promo-menu-enabled">Hiển thị</Label>
              <Switch id="promo-menu-enabled" checked={menuEnabled} onCheckedChange={setMenuEnabled} />
            </div>
          </div>
          <Textarea
            className="min-h-24"
            value={menuText}
            onChange={(event) => setMenuText(event.target.value)}
            placeholder="Ví dụ: Mua đủ 10 đơn bất kỳ nhận mã giảm giá cho đơn tiếp theo. Nếu có mã còn hiệu lực, bot sẽ tự áp khi tạo đơn."
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={syncSettings}>Hoàn tác</Button>
            <Button onClick={saveSettings} disabled={saving}>Lưu thông báo</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[820px]">
            <TableHeader>
              <TableRow>
                <TableHead>Mã</TableHead>
                <TableHead className="text-center">Giảm</TableHead>
                <TableHead className="text-center">Mốc đơn</TableHead>
                <TableHead className="text-center">Hạn dùng</TableHead>
                <TableHead className="text-center">Trạng thái</TableHead>
                <TableHead>Ghi chú</TableHead>
                <TableHead className="text-center">Sửa</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {promotions.map((promo) => (
                <TableRow key={text(promo.id || promo.code)}>
                  <TableCell><code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(promo.code)}</code></TableCell>
                  <TableCell className="text-center">{money(promo.discount_amount || promo.discount_percent)}</TableCell>
                  <TableCell className="text-center">{text(promo.required_orders)} đơn</TableCell>
                  <TableCell className="text-center">{text(promo.expires_days)} ngày</TableCell>
                  <TableCell className="text-center"><Badge variant={text(promo.status) === "PAUSED" ? "outline" : "default"}>{text(promo.status)}</Badge></TableCell>
                  <TableCell className="max-w-[260px] truncate text-muted-foreground">{text(promo.note)}</TableCell>
                  <TableCell className="text-center">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(promo)}><Pencil size={14} /></Button>
                  </TableCell>
                </TableRow>
              ))}
              {!promotions.length && <TableRow><TableCell colSpan={7} className="py-8 text-center text-muted-foreground">Chưa có mã khuyến mãi</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[760px]">
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Mã đã tặng</TableHead>
                <TableHead className="text-center">Giảm</TableHead>
                <TableHead className="text-center">Trạng thái</TableHead>
                <TableHead>Hạn dùng</TableHead>
                <TableHead>Đơn đã dùng</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {awards.slice(0, 80).map((award, index) => (
                <TableRow key={`${text(award.user_id)}-${text(award.code)}-${index}`}>
                  <TableCell className="font-mono text-xs">{text(award.user_id)}</TableCell>
                  <TableCell><code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(award.code)}</code></TableCell>
                  <TableCell className="text-center">{money(award.discount_amount || award.discount_percent)}</TableCell>
                  <TableCell className="text-center"><Badge variant={text(award.status) === "USED" ? "secondary" : "default"}>{text(award.status)}</Badge></TableCell>
                  <TableCell className="text-xs text-muted-foreground">{text(award.expires_at)}</TableCell>
                  <TableCell className="font-mono text-xs">{text(award.used_order_id)}</TableCell>
                </TableRow>
              ))}
              {!awards.length && <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">Chưa tặng mã nào</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{form.id ? "Sửa mã khuyến mãi" : "Thêm mã khuyến mãi"}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1"><Label>Mã gốc</Label><Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} placeholder="THANK10" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1"><Label>Số tiền giảm</Label><Input type="number" min="1" value={form.discount_amount} onChange={(e) => setForm({ ...form, discount_amount: e.target.value })} /></div>
              <div className="space-y-1"><Label>Đơn tối thiểu</Label><Input type="number" min="0" value={form.min_order_total} onChange={(e) => setForm({ ...form, min_order_total: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1"><Label>Mốc đơn</Label><Input type="number" min="1" value={form.required_orders} onChange={(e) => setForm({ ...form, required_orders: e.target.value })} /></div>
              <div className="space-y-1"><Label>Hạn ngày</Label><Input type="number" min="1" value={form.expires_days} onChange={(e) => setForm({ ...form, expires_days: e.target.value })} /></div>
            </div>
            <div className="space-y-1">
              <Label>Trạng thái</Label>
              <Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">ACTIVE</SelectItem>
                  <SelectItem value="PAUSED">PAUSED</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label>Ghi chú</Label><Input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Hủy</Button>
            <Button onClick={save} disabled={saving || !form.code}>{saving ? "Đang lưu..." : "Lưu"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
