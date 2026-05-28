import { useState } from "react";
import { Pencil, Plus, Ticket } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../ui/dialog";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Textarea } from "../ui/textarea";
import { adminApi, money, text, type AdminSnapshot, type AnyRow } from "../../api";

interface Props {
  data: AdminSnapshot | null;
  adminKey: string;
  refresh: () => Promise<void>;
}

const EMPTY = {
  slot_id: "",
  title: "",
  price: "0",
  total_slots: "5",
  status: "OPEN",
  note: "",
};

const blank = (value: unknown) => {
  const normalized = text(value);
  return normalized === "â€”" || normalized === "Ã¢â‚¬â€";
};

export function Slots({ data, adminKey, refresh }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ ...EMPTY });
  const [saving, setSaving] = useState(false);

  const slots = data?.slots || [];
  const participants = data?.slot_participants || [];

  const openAdd = () => {
    setForm({ ...EMPTY });
    setOpen(true);
  };

  const openEdit = (slot: AnyRow) => {
    setForm({
      slot_id: blank(slot.slot_id) ? "" : text(slot.slot_id),
      title: blank(slot.title) ? "" : text(slot.title),
      price: blank(slot.price) ? "0" : text(slot.price),
      total_slots: blank(slot.total_slots) ? "5" : text(slot.total_slots),
      status: text(slot.status).toUpperCase() === "CLOSED" ? "CLOSED" : "OPEN",
      note: blank(slot.note) ? "" : text(slot.note),
    });
    setOpen(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      await adminApi("/admin/api/slots", adminKey, { method: "POST", body: JSON.stringify(form) });
      toast.success("Da luu slot");
      setOpen(false);
      await refresh();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2"><Ticket size={20} /> Slot</h2>
        <Button size="sm" className="gap-1.5" onClick={openAdd}><Plus size={15} /> Them slot</Button>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[940px]">
            <TableHeader>
              <TableRow>
                <TableHead>Slot</TableHead>
                <TableHead className="text-center">Gia</TableHead>
                <TableHead className="text-center">Tong slot</TableHead>
                <TableHead className="text-center">Da tra</TableHead>
                <TableHead className="text-center">Con lai</TableHead>
                <TableHead className="text-center">Trang thai</TableHead>
                <TableHead>Ghi chu</TableHead>
                <TableHead className="text-center">Sua</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {slots.map((slot) => (
                <TableRow key={text(slot.slot_id)}>
                  <TableCell>
                    <div className="font-medium">{text(slot.title)}</div>
                    <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(slot.slot_id)}</code>
                  </TableCell>
                  <TableCell className="text-center">{money(slot.price)}</TableCell>
                  <TableCell className="text-center">{text(slot.total_slots)}</TableCell>
                  <TableCell className="text-center">{text(slot.paid_count)}</TableCell>
                  <TableCell className="text-center">{text(slot.remaining)}</TableCell>
                  <TableCell className="text-center"><Badge variant={text(slot.status).toUpperCase() === "CLOSED" ? "outline" : "default"}>{text(slot.status)}</Badge></TableCell>
                  <TableCell className="max-w-[280px] truncate text-muted-foreground">{text(slot.note)}</TableCell>
                  <TableCell className="text-center">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(slot)}><Pencil size={14} /></Button>
                  </TableCell>
                </TableRow>
              ))}
              {!slots.length && <TableRow><TableCell colSpan={8} className="py-8 text-center text-muted-foreground">Chua co slot nao</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[1100px]">
            <TableHeader>
              <TableRow>
                <TableHead>Slot</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>User ID</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>Ho ten</TableHead>
                <TableHead>Order</TableHead>
                <TableHead className="text-center">Trang thai</TableHead>
                <TableHead>Paid at</TableHead>
                <TableHead>Joined at</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {participants.slice(0, 200).map((item, index) => (
                <TableRow key={`${text(item.order_id)}-${index}`}>
                  <TableCell><code className="rounded bg-muted px-1.5 py-0.5 text-xs">{text(item.slot_id)}</code></TableCell>
                  <TableCell className="font-medium">{text(item.email)}</TableCell>
                  <TableCell className="font-mono text-xs">{text(item.user_id)}</TableCell>
                  <TableCell className="text-blue-600">{text(item.username)}</TableCell>
                  <TableCell>{text(item.full_name)}</TableCell>
                  <TableCell className="font-mono text-xs">{text(item.order_id)}</TableCell>
                  <TableCell className="text-center"><Badge variant={text(item.status).toUpperCase() === "PAID" ? "default" : "secondary"}>{text(item.status)}</Badge></TableCell>
                  <TableCell className="text-xs text-muted-foreground">{text(item.paid_at)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{text(item.joined_at)}</TableCell>
                </TableRow>
              ))}
              {!participants.length && <TableRow><TableCell colSpan={9} className="py-8 text-center text-muted-foreground">Chua co ai mua slot</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>{form.slot_id ? "Sua slot" : "Them slot"}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1">
              <Label>Ten slot</Label>
              <Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Slot ChatGPT Team thang 6" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Gia</Label>
                <Input type="number" min="0" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>Tong slot</Label>
                <Input type="number" min="0" value={form.total_slots} onChange={(event) => setForm({ ...form, total_slots: event.target.value })} />
              </div>
            </div>
            <div className="space-y-1">
              <Label>Trang thai</Label>
              <Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="OPEN">OPEN</SelectItem>
                  <SelectItem value="CLOSED">CLOSED</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Ghi chu</Label>
              <Textarea className="min-h-20" value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} placeholder="Thong tin admin can xem noi bo" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Huy</Button>
            <Button onClick={save} disabled={saving || !form.title}>{saving ? "Dang luu..." : "Luu"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
