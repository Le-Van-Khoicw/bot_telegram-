import { useEffect, useState } from "react";
import { Gift, Pencil, Plus, Trash2 } from "lucide-react";
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
  promo_type: "AMOUNT",
  discount_amount: "20000",
  min_order_total: "0",
  stock_code: "",
  threshold_amount: "500000",
  required_orders: "0",
  threshold_qty: "0",
  max_claims: "0",
  target_user_id: "",
  expires_days: "7",
  status: "ACTIVE",
  note: "",
};

const blank = (value: unknown) => {
  const normalized = text(value);
  return normalized === "—" || normalized === "â€”";
};

const moneyInputToNumber = (value: string) => {
  let raw = String(value || "").trim().toLowerCase();
  if (!raw) return "0";
  let multiplier = 1;
  if (/(k|nghin|nghìn)$/.test(raw)) {
    multiplier = 1000;
    raw = raw.replace(/(k|nghin|nghìn)$/, "").trim();
  } else if (/(m|tr|trieu|triệu)$/.test(raw)) {
    multiplier = 1000000;
    raw = raw.replace(/(m|tr|trieu|triệu)$/, "").trim();
  }
  if (multiplier > 1) {
    const num = Number(raw.replace(/[^0-9,.]/g, "").replace(",", "."));
    return String(Math.max(0, Math.round((Number.isFinite(num) ? num : 0) * multiplier)));
  }
  return raw.replace(/[^\d]/g, "") || "0";
};

const statusLabel = (status: unknown) => text(status).toUpperCase() === "PAUSED" ? "Tắt" : "Bật";

const plainNumber = (value: string) => String(value || "").replace(/[^\d]/g, "") || "0";

const shortMoney = (value: string) => money(moneyInputToNumber(value));

export function Promotions({ data, adminKey, refresh }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ ...EMPTY });
  const settings = data?.promo_settings || {};
  const [menuEnabled, setMenuEnabled] = useState(String(settings.menu_enabled || "").toUpperCase() === "TRUE");
  const [menuText, setMenuText] = useState(String(settings.menu_text || ""));
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const promotions = data?.promotions || [];
  const awards = data?.promo_awards || [];
  const stockOptions = Array.from(
    new Set((data?.products || []).map((product) => text(product.stock_code)).filter((stock) => stock && !blank(stock)))
  ).sort();
  const promoRulePreview = [
    `Giam ${shortMoney(form.discount_amount)}`,
    `chi ap dung khi tong tien don tu ${shortMoney(form.min_order_total)}`,
    form.stock_code ? `stock ${form.stock_code}` : "tat ca san pham",
    form.promo_type === "AMOUNT" ? `tu tang ma khi khach tich du ${shortMoney(form.threshold_amount)}` :
      form.promo_type === "ORDER_QTY" ? `tu tang ma khi 1 don mua tu ${form.threshold_qty || 0} san pham` :
      form.promo_type === "ORDER_COUNT" ? `tu tang ma sau ${form.required_orders || 0} don da giao` :
      form.promo_type === "PRIVATE" ? `ma rieng cho user ${form.target_user_id || "chua nhap"}` :
      "ma public, khach nhap ma goc de nhan ma rieng",
    Number(form.max_claims || 0) > 0 ? `toi da ${form.max_claims} ma` : "khong gioi han so ma",
  ].join(" | ");

  const syncSettings = () => {
    setMenuEnabled(String(settings.menu_enabled || "").toUpperCase() === "TRUE");
    setMenuText(String(settings.menu_text || ""));
  };

  useEffect(() => {
    syncSettings();
  }, [settings.menu_enabled, settings.menu_text]);

  const openAdd = () => {
    setForm({ ...EMPTY });
    setOpen(true);
  };

  const openEdit = (promo: AnyRow) => {
    setForm({
      id: blank(promo.id) ? "" : text(promo.id),
      code: blank(promo.code) ? "" : text(promo.code),
      promo_type: blank(promo.promo_type) ? "ORDER_COUNT" : text(promo.promo_type),
      discount_amount: blank(promo.discount_amount || promo.discount_percent) ? "20000" : text(promo.discount_amount || promo.discount_percent),
      min_order_total: blank(promo.min_order_total) ? "0" : text(promo.min_order_total),
      stock_code: blank(promo.stock_code) ? "" : text(promo.stock_code),
      threshold_amount: blank(promo.threshold_amount) ? "0" : text(promo.threshold_amount),
      required_orders: blank(promo.required_orders) ? "0" : text(promo.required_orders),
      threshold_qty: blank(promo.threshold_qty) ? "0" : text(promo.threshold_qty),
      max_claims: blank(promo.max_claims) ? "0" : text(promo.max_claims),
      target_user_id: blank(promo.target_user_id) ? "" : text(promo.target_user_id),
      expires_days: blank(promo.expires_days) ? "7" : text(promo.expires_days),
      status: text(promo.status) === "PAUSED" ? "PAUSED" : "ACTIVE",
      note: blank(promo.note) ? "" : text(promo.note),
    });
    setOpen(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      await adminApi("/admin/api/promotions", adminKey, {
        method: "POST",
        body: JSON.stringify({
          ...form,
          discount_amount: moneyInputToNumber(form.discount_amount),
          min_order_total: moneyInputToNumber(form.min_order_total),
          threshold_amount: moneyInputToNumber(form.threshold_amount),
          required_orders: plainNumber(form.required_orders),
          threshold_qty: plainNumber(form.threshold_qty),
          max_claims: plainNumber(form.max_claims),
        }),
      });
      toast.success("Da luu khuyen mai");
      setOpen(false);
      await refresh();
    } finally {
      setSaving(false);
    }
  };

  const deleteCurrent = async () => {
    const promoId = form.id.trim();
    if (!promoId) return;
    const ok = window.confirm(`Xóa mã khuyến mãi ${form.code || promoId}?`);
    if (!ok) return;
    setDeleting(true);
    try {
      await adminApi(`/admin/api/promotions/${encodeURIComponent(promoId)}`, adminKey, { method: "DELETE" });
      toast.success("Da xoa ma khuyen mai");
      setOpen(false);
      await refresh();
    } finally {
      setDeleting(false);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const result = await adminApi<{ settings?: AnyRow }>("/admin/api/promo-settings", adminKey, {
        method: "POST",
        body: JSON.stringify({ menu_enabled: menuEnabled, menu_text: menuText }),
      });
      if (result.settings) {
        setMenuEnabled(String(result.settings.menu_enabled || "").toUpperCase() === "TRUE");
        setMenuText(String(result.settings.menu_text || ""));
      }
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
            placeholder="Vi du: Mua du moc se nhan ma rieng. Khi thanh toan, bam Nhap ma khuyen mai va dan ma cua ban de duoc giam."
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
                <TableHead>Loai</TableHead>
                <TableHead className="text-center">Giam</TableHead>
                <TableHead className="text-center">Tien don toi thieu</TableHead>
                <TableHead className="text-center">Moc nhan ma</TableHead>
                <TableHead className="text-center">So ma toi da</TableHead>
                <TableHead className="text-center">Stock</TableHead>
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
                  <TableCell className="text-xs">{text(promo.promo_type || "ORDER_COUNT")}</TableCell>
                  <TableCell className="text-center">{money(promo.discount_amount || promo.discount_percent)}</TableCell>
                  <TableCell className="text-center">{money(promo.min_order_total)}</TableCell>
                  <TableCell className="text-center">
                    {text(promo.promo_type) === "AMOUNT" ? money(promo.threshold_amount) :
                      text(promo.promo_type) === "ORDER_QTY" ? `${text(promo.threshold_qty)} sp / 1 don` :
                      text(promo.promo_type) === "PRIVATE" ? `User ${text(promo.target_user_id)}` :
                      Number(promo.required_orders || 0) > 0 ? `${text(promo.required_orders)} don` : "Public"}
                  </TableCell>
                  <TableCell className="text-center">{Number(promo.max_claims || 0) > 0 ? text(promo.max_claims) : "Khong gioi han"}</TableCell>
                  <TableCell className="text-center">{blank(promo.stock_code) ? "Tat ca" : <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(promo.stock_code)}</code>}</TableCell>
                  <TableCell className="text-center">{text(promo.expires_days)} ngay</TableCell>
                  <TableCell className="text-center"><Badge variant={text(promo.status) === "PAUSED" ? "outline" : "default"}>{statusLabel(promo.status)}</Badge></TableCell>
                  <TableCell className="max-w-[260px] truncate text-muted-foreground">{text(promo.note)}</TableCell>
                  <TableCell className="text-center">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(promo)}><Pencil size={14} /></Button>
                  </TableCell>
                </TableRow>
              ))}
              {!promotions.length && <TableRow><TableCell colSpan={11} className="py-8 text-center text-muted-foreground">Chua co ma khuyen mai</TableCell></TableRow>}
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
                <TableHead className="text-center">Lan</TableHead>
                <TableHead>Ma da tang</TableHead>
                <TableHead className="text-center">Giam</TableHead>
                <TableHead className="text-center">Tien don toi thieu</TableHead>
                <TableHead className="text-center">Stock</TableHead>
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
                  <TableCell className="text-center">{text(award.cycle)}</TableCell>
                  <TableCell><code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(award.code)}</code></TableCell>
                  <TableCell className="text-center">{money(award.discount_amount || award.discount_percent)}</TableCell>
                  <TableCell className="text-center">{money(award.min_order_total)}</TableCell>
                  <TableCell className="text-center">{blank(award.stock_code) ? "Tat ca" : <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(award.stock_code)}</code>}</TableCell>
                  <TableCell className="text-center"><Badge variant={text(award.status) === "USED" ? "secondary" : "default"}>{text(award.status)}</Badge></TableCell>
                  <TableCell className="text-xs text-muted-foreground">{text(award.expires_at)}</TableCell>
                  <TableCell className="font-mono text-xs">{text(award.used_order_id)}</TableCell>
                </TableRow>
              ))}
              {!awards.length && <TableRow><TableCell colSpan={11} className="py-8 text-center text-muted-foreground">Chua tang ma nao</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{form.id ? "Sua ma khuyen mai" : "Them ma khuyen mai"}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1"><Label>Ma goc</Label><Input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })} placeholder="THANK10" /></div>
            <div className="space-y-1">
              <Label>Kieu phat ma</Label>
              <Select value={form.promo_type} onValueChange={(value) => setForm({ ...form, promo_type: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="AMOUNT">Tich tien du moc</SelectItem>
                  <SelectItem value="ORDER_COUNT">Tich so don da giao</SelectItem>
                  <SelectItem value="ORDER_QTY">Mot don mua du so luong</SelectItem>
                  <SelectItem value="PUBLIC">Ma public co gioi han luot</SelectItem>
                  <SelectItem value="PRIVATE">Ma rieng cho 1 user</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
              <div className="font-medium text-foreground">Tom tat luat</div>
              <div className="mt-1">{promoRulePreview}</div>
              <div className="mt-2 text-xs">Thong bao trong menu bot chi la noi dung quang cao. Bot tinh giam gia theo cac o ben duoi.</div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>So tien giam (VND)</Label>
                <Input inputMode="numeric" value={form.discount_amount} onChange={(event) => setForm({ ...form, discount_amount: event.target.value })} placeholder="VD: 20k, 20.000" />
                <p className="text-xs text-muted-foreground">Nhap so tien se tru vao don.</p>
              </div>
              <div className="space-y-1">
                <Label>Tien don toi thieu (VND)</Label>
                <Input inputMode="numeric" value={form.min_order_total} onChange={(event) => setForm({ ...form, min_order_total: event.target.value })} placeholder="VD: 500k, 500.000" />
                <p className="text-xs text-muted-foreground">Day la tong tien don hang, khong phai so don.</p>
              </div>
            </div>
            {form.promo_type === "AMOUNT" && (
              <div className="space-y-1">
                <Label>Tich tien du bao nhieu thi tang ma</Label>
                <Input inputMode="numeric" value={form.threshold_amount} onChange={(event) => setForm({ ...form, threshold_amount: event.target.value })} placeholder="VD: 500k, 500.000" />
                <p className="text-xs text-muted-foreground">Khach mua nhieu don da giao se duoc cong don tien.</p>
              </div>
            )}
            {form.promo_type === "ORDER_COUNT" && (
              <div className="space-y-1">
                <Label>Tang ma sau bao nhieu don da giao</Label>
                <Input inputMode="numeric" value={form.required_orders} onChange={(event) => setForm({ ...form, required_orders: plainNumber(event.target.value) })} placeholder="VD: 10" />
                <p className="text-xs text-muted-foreground">Nhap 10 nghia la khach mua du 10 don da giao thi bot moi tang ma.</p>
              </div>
            )}
            {form.promo_type === "ORDER_QTY" && (
              <div className="space-y-1">
                <Label>Mot don mua tu bao nhieu san pham thi tang ma</Label>
                <Input inputMode="numeric" value={form.threshold_qty} onChange={(event) => setForm({ ...form, threshold_qty: plainNumber(event.target.value) })} placeholder="VD: 10" />
                <p className="text-xs text-muted-foreground">Chi tinh khi cung mot don co so luong dat moc nay.</p>
              </div>
            )}
            {form.promo_type === "PRIVATE" && (
              <div className="space-y-1">
                <Label>User ID nhan ma rieng</Label>
                <Input inputMode="numeric" value={form.target_user_id} onChange={(event) => setForm({ ...form, target_user_id: plainNumber(event.target.value) })} placeholder="VD: 6261937216" />
                <p className="text-xs text-muted-foreground">Chi user nay moi dung duoc ma con duoc tao.</p>
              </div>
            )}
            <div className="space-y-1">
              <Label>So ma toi da duoc phat</Label>
              <Input inputMode="numeric" value={form.max_claims} onChange={(event) => setForm({ ...form, max_claims: plainNumber(event.target.value) })} placeholder="0 = khong gioi han, VD: 20" />
              <p className="text-xs text-muted-foreground">Nhap 20 thi chi 20 ma con dau tien duoc tao. Moi khach nhan mot ma rieng.</p>
            </div>
            <div className="space-y-1">
              <Label>Stock Code ap dung khi dung ma</Label>
              <Select value={form.stock_code || "__ALL__"} onValueChange={(value) => setForm({ ...form, stock_code: value === "__ALL__" ? "" : value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__ALL__">Tat ca san pham</SelectItem>
                  {stockOptions.map((stock) => (
                    <SelectItem key={stock} value={stock}>{stock}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label>Han ngay</Label><Input type="number" min="1" value={form.expires_days} onChange={(event) => setForm({ ...form, expires_days: event.target.value })} /></div>
            <div className="space-y-1">
              <Label>Trang thai</Label>
              <Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">Bật - mã đang chạy</SelectItem>
                  <SelectItem value="PAUSED">Tắt - ngưng mã</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label>Ghi chu</Label><Input value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} /></div>
          </div>
          <DialogFooter>
            {form.id && (
              <Button variant="destructive" className="mr-auto gap-1.5" onClick={deleteCurrent} disabled={saving || deleting}>
                <Trash2 size={15} />
                {deleting ? "Dang xoa..." : "Xoa"}
              </Button>
            )}
            <Button variant="outline" onClick={() => setOpen(false)}>Huy</Button>
            <Button onClick={save} disabled={saving || deleting || !form.code}>{saving ? "Dang luu..." : "Luu"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
