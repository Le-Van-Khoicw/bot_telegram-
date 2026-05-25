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

const EMPTY = {
  id: "",
  code: "",
  discount_amount: "20000",
  min_order_total: "0",
  required_orders: "10",
  expires_days: "7",
  status: "ACTIVE",
  note: "",
};

const blank = (value: unknown) => {
  const normalized = text(value);
  return normalized === "—" || normalized === "â€”";
};

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
      id: blank(promo.id) ? "" : text(promo.id),
      code: blank(promo.code) ? "" : text(promo.code),
      discount_amount: blank(promo.discount_amount || promo.discount_percent) ? "20000" : text(promo.discount_amount || promo.discount_percent),
      min_order_total: blank(promo.min_order_total) ? "0" : text(promo.min_order_total),
      required_orders: blank(promo.required_orders) ? "10" : text(promo.required_orders),
      expires_days: blank(promo.expires_days) ? "7" : text(promo.expires_days),
      status: text(promo.status) === "PAUSED" ? "PAUSED" : "ACTIVE",
      note: blank(promo.note) ? "" : text(promo.note),
    });
    setOpen(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      await adminApi("/admin/api/promotions", adminKey, { method: "POST", body: JSON.stringify(form) });
      toast.success("Da luu khuyen mai");
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
      toast.success("Da luu thong bao menu");
      await refresh();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2"><Gift size={20} /> Khuyen mai</h2>
        <Button size="sm" className="gap-1.5" onClick={openAdd}><Plus size={15} /> Them ma</Button>
      </div>

      <Card className="shadow-sm">
        <CardContent className="space-y-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">Thong bao khuyen mai trong menu bot</h3>
              <p className="text-xs text-muted-foreground">Noi dung nay se hien trong /shop khi bat.</p>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="promo-menu-enabled">Hien thi</Label>
              <Switch id="promo-menu-enabled" checked={menuEnabled} onCheckedChange={setMenuEnabled} />
            </div>
          </div>
          <Textarea
            className="min-h-24"
            value={menuText}
            onChange={(event) => setMenuText(event.target.value)}
            placeholder="Vi du: Mua du 10 don bat ky nhan ma giam gia cho don tiep theo. Neu co ma con hieu luc, bot se tu ap khi tao don."
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={syncSettings}>Hoan tac</Button>
            <Button onClick={saveSettings} disabled={saving}>Luu thong bao</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[920px]">
            <TableHeader>
              <TableRow>
                <TableHead>Ma</TableHead>
                <TableHead className="text-center">Giam</TableHead>
                <TableHead className="text-center">Don toi thieu</TableHead>
                <TableHead className="text-center">Moc don</TableHead>
                <TableHead className="text-center">Han dung</TableHead>
                <TableHead className="text-center">Trang thai</TableHead>
                <TableHead>Ghi chu</TableHead>
                <TableHead className="text-center">Sua</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {promotions.map((promo) => (
                <TableRow key={text(promo.id || promo.code)}>
                  <TableCell><code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(promo.code)}</code></TableCell>
                  <TableCell className="text-center">{money(promo.discount_amount || promo.discount_percent)}</TableCell>
                  <TableCell className="text-center">{money(promo.min_order_total)}</TableCell>
                  <TableCell className="text-center">{text(promo.required_orders)} don</TableCell>
                  <TableCell className="text-center">{text(promo.expires_days)} ngay</TableCell>
                  <TableCell className="text-center"><Badge variant={text(promo.status) === "PAUSED" ? "outline" : "default"}>{text(promo.status)}</Badge></TableCell>
                  <TableCell className="max-w-[260px] truncate text-muted-foreground">{text(promo.note)}</TableCell>
                  <TableCell className="text-center">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(promo)}><Pencil size={14} /></Button>
                  </TableCell>
                </TableRow>
              ))}
              {!promotions.length && <TableRow><TableCell colSpan={8} className="py-8 text-center text-muted-foreground">Chua co ma khuyen mai</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[980px]">
            <TableHeader>
              <TableRow>
                <TableHead>User ID</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>Ho ten</TableHead>
                <TableHead>Ma da tang</TableHead>
                <TableHead className="text-center">Giam</TableHead>
                <TableHead className="text-center">Don toi thieu</TableHead>
                <TableHead className="text-center">Trang thai</TableHead>
                <TableHead>Han dung</TableHead>
                <TableHead>Don da dung</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {awards.slice(0, 80).map((award, index) => (
                <TableRow key={`${text(award.user_id)}-${text(award.code)}-${index}`}>
                  <TableCell className="font-mono text-xs">{text(award.user_id)}</TableCell>
                  <TableCell className="text-sm text-blue-600">{text(award.username)}</TableCell>
                  <TableCell className="text-sm">{text(award.full_name)}</TableCell>
                  <TableCell><code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(award.code)}</code></TableCell>
                  <TableCell className="text-center">{money(award.discount_amount || award.discount_percent)}</TableCell>
                  <TableCell className="text-center">{money(award.min_order_total)}</TableCell>
                  <TableCell className="text-center"><Badge variant={text(award.status) === "USED" ? "secondary" : "default"}>{text(award.status)}</Badge></TableCell>
                  <TableCell className="text-xs text-muted-foreground">{text(award.expires_at)}</TableCell>
                  <TableCell className="font-mono text-xs">{text(award.used_order_id)}</TableCell>
                </TableRow>
              ))}
              {!awards.length && <TableRow><TableCell colSpan={9} className="py-8 text-center text-muted-foreground">Chua tang ma nao</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{form.id ? "Sua ma khuyen mai" : "Them ma khuyen mai"}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1"><Label>Ma goc</Label><Input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })} placeholder="THANK10" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1"><Label>So tien giam</Label><Input type="number" min="1" value={form.discount_amount} onChange={(event) => setForm({ ...form, discount_amount: event.target.value })} /></div>
              <div className="space-y-1"><Label>Don toi thieu</Label><Input type="number" min="0" value={form.min_order_total} onChange={(event) => setForm({ ...form, min_order_total: event.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1"><Label>Moc don</Label><Input type="number" min="1" value={form.required_orders} onChange={(event) => setForm({ ...form, required_orders: event.target.value })} /></div>
              <div className="space-y-1"><Label>Han ngay</Label><Input type="number" min="1" value={form.expires_days} onChange={(event) => setForm({ ...form, expires_days: event.target.value })} /></div>
            </div>
            <div className="space-y-1">
              <Label>Trang thai</Label>
              <Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">ACTIVE</SelectItem>
                  <SelectItem value="PAUSED">PAUSED</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label>Ghi chu</Label><Input value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Huy</Button>
            <Button onClick={save} disabled={saving || !form.code}>{saving ? "Dang luu..." : "Luu"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
