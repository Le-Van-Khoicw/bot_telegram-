import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Clipboard, Copy, PackageCheck, RotateCcw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { adminApi, text, type AdminSnapshot } from "../../api";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Textarea } from "../ui/textarea";

type MaterialStatus = "NEW" | "OK" | "BAD";
type MaterialItem = { id: string; value: string; status: MaterialStatus; note?: string };

interface Props {
  data: AdminSnapshot | null;
  adminKey: string;
  refresh: () => Promise<void>;
}

const STORAGE_KEY = "admin_material_items_v1";
const BACKUP_KEY = "admin_material_items_backup_v1";

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function loadItems(): MaterialItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) {
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed : [];
    }

    const backup = JSON.parse(localStorage.getItem(BACKUP_KEY) || "[]");
    return Array.isArray(backup) ? backup : [];
  } catch {
    return [];
  }
}

function saveItems(items: MaterialItem[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  if (items.length > 0) {
    localStorage.setItem(BACKUP_KEY, JSON.stringify(items));
  } else {
    localStorage.removeItem(BACKUP_KEY);
  }
}

function normalizeItems(rows: any[]): MaterialItem[] {
  return (rows || [])
    .map((row) => {
      const status = String(row.status || "NEW").toUpperCase();
      return {
        id: String(row.id || makeId()),
        value: String(row.value || "").trim(),
        status: (status === "OK" || status === "BAD" ? status : "NEW") as MaterialStatus,
        note: row.note ? String(row.note) : undefined,
      };
    })
    .filter((item) => item.value);
}

function materialKey(value: any) {
  const rawValue = String(value || "").trim();
  const firstPart = rawValue.split("|")[0]?.split("----")[0]?.trim() || rawValue;
  return firstPart.toLowerCase();
}

export function Materials({ data, adminKey, refresh }: Props) {
  const [raw, setRaw] = useState("");
  const [stockCode, setStockCode] = useState("");
  const [items, setItems] = useState<MaterialItem[]>(loadItems);
  const [busy, setBusy] = useState(false);
  const [syncState, setSyncState] = useState<"synced" | "pending" | "saving" | "error">("synced");
  const retryTimerRef = useRef<number | null>(null);
  const autosaveTimerRef = useRef<number | null>(null);
  const pendingSaveRef = useRef<MaterialItem[] | null>(null);
  const pendingOptionsRef = useRef<{ upsertItems?: MaterialItem[]; deletedIds?: string[]; forceClear?: boolean } | null>(null);
  const warnedSaveErrorRef = useRef(false);
  const syncStateRef = useRef(syncState);

  useEffect(() => {
    syncStateRef.current = syncState;
  }, [syncState]);

  const applyRemoteItems = useCallback((rows: any[] | undefined, allowEmpty = false) => {
    const synced = normalizeItems(rows || []);
    setItems(synced);
    saveItems(synced);
  }, []);

  const productCodes = useMemo(() => {
    const codes = (data?.products || []).map((p) => text(p.stock_code)).filter((x) => x !== "—");
    return Array.from(new Set(codes)).sort();
  }, [data]);

  const counts = useMemo(() => ({
    NEW: items.filter((x) => x.status === "NEW").length,
    OK: items.filter((x) => x.status === "OK").length,
    BAD: items.filter((x) => x.status === "BAD").length,
  }), [items]);

  const saveRemote = useCallback(async (
    next: MaterialItem[],
    options: { upsertItems?: MaterialItem[]; deletedIds?: string[]; forceClear?: boolean } = {},
  ): Promise<boolean> => {
    try {
      setSyncState("saving");
      const result = await adminApi<{ items?: any[] }>("/admin/api/materials", adminKey, {
        method: "POST",
        body: JSON.stringify({
          items: options.upsertItems ?? next,
          deleted_ids: options.deletedIds || [],
          force_clear: Boolean(options.forceClear),
        }),
      });
      if (result.items) {
        applyRemoteItems(result.items, Boolean(options.forceClear) || next.length === 0);
      }
      pendingSaveRef.current = null;
      pendingOptionsRef.current = null;
      warnedSaveErrorRef.current = false;
      setSyncState("synced");
      return true;
    } catch (error) {
      pendingSaveRef.current = next;
      pendingOptionsRef.current = options;
      setSyncState("error");
      if (!warnedSaveErrorRef.current) {
        warnedSaveErrorRef.current = true;
        const message = error instanceof Error ? error.message : "";
        const isQuota = message.toLowerCase().includes("quota exceeded");
        toast.warning(isQuota
          ? "Google Sheet đang giới hạn lượt ghi. Dữ liệu đã lưu tạm trên máy, hãy đồng bộ lại sau vài phút."
          : "Đã lưu tạm trên máy. Web sẽ thử đồng bộ lại sau."
        );
      }
      if (retryTimerRef.current) {
        window.clearTimeout(retryTimerRef.current);
      }
      retryTimerRef.current = window.setTimeout(() => {
        retryTimerRef.current = null;
        const pending = pendingSaveRef.current;
        const pendingOptions = pendingOptionsRef.current || {};
        if (pending) void saveRemote(pending, pendingOptions);
      }, 300000);
      return false;
    }
  }, [adminKey]);

  const fetchRemoteMaterials = useCallback(async () => {
    if (!adminKey || pendingSaveRef.current || syncStateRef.current === "saving") return;
    const result = await adminApi<{ items?: any[] }>("/admin/api/materials", adminKey);
    applyRemoteItems(result.items, false);
  }, [adminKey, applyRemoteItems]);

  useEffect(() => () => {
    if (retryTimerRef.current) {
      window.clearTimeout(retryTimerRef.current);
    }
    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
    }
  }, []);

  useEffect(() => {
    if (!adminKey) return;
    void fetchRemoteMaterials().catch(() => undefined);
    const timer = window.setInterval(() => {
      void fetchRemoteMaterials().catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [adminKey, fetchRemoteMaterials]);

  useEffect(() => {
    if (!data) return;
    if (pendingSaveRef.current || syncStateRef.current === "saving") return;
    applyRemoteItems(data.materials || [], false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.generated_at, applyRemoteItems]);

  const setAndSave = (
    next: MaterialItem[],
    options: { upsertItems?: MaterialItem[]; deletedIds?: string[]; forceClear?: boolean } = {},
  ) => {
    setItems(next);
    saveItems(next);
    pendingSaveRef.current = next;
    pendingOptionsRef.current = options;
    setSyncState("pending");
    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
    }
    autosaveTimerRef.current = window.setTimeout(() => {
      autosaveTimerRef.current = null;
      void saveRemote(next, options);
    }, 800);
  };

  const importRaw = () => {
    const lines = raw.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
    if (!lines.length) return;
    const existed = new Set(items.map((x) => x.value));
    const added = lines
      .filter((line) => !existed.has(line))
      .map((line) => ({ id: makeId(), value: line, status: "NEW" as const }));
    const next = [
      ...items,
      ...added,
    ];
    setRaw("");
    setAndSave(next, { upsertItems: added });
    toast.success(`Đã nhập ${next.length - items.length} dòng nguyên liệu`);
  };

  const updateStatus = (id: string, status: MaterialStatus) => {
    const changed = items.find((item) => item.id === id);
    if (!changed) return;
    const updated = { ...changed, status };
    setAndSave(items.map((item) => item.id === id ? updated : item), { upsertItems: [updated] });
  };

  const bulkUpdateStatus = (from: MaterialStatus, to: MaterialStatus) => {
    const changed = items.filter((item) => item.status === from).length;
    if (!changed) return toast.info("Không có dòng nào để chuyển");
    const changedItems = items.filter((item) => item.status === from).map((item) => ({ ...item, status: to }));
    setAndSave(
      items.map((item) => item.status === from ? { ...item, status: to } : item),
      { upsertItems: changedItems },
    );
    toast.success(`Đã chuyển ${changed} dòng sang ${to === "OK" ? "OK" : "Lỗi"}`);
  };

  const clearStatus = async (status?: MaterialStatus) => {
    const next = status ? items.filter((item) => item.status !== status) : [];
    const deletedIds = status
      ? items.filter((item) => item.status === status).map((item) => item.id)
      : items.map((item) => item.id);
    if (!deletedIds.length) return;
    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }
    const options = { upsertItems: next, deletedIds, forceClear: !status || next.length === 0 };
    setItems(next);
    saveItems(next);
    pendingSaveRef.current = next;
    pendingOptionsRef.current = options;
    const saved = await saveRemote(next, options);
    if (saved) toast.success(`Đã xóa ${deletedIds.length} dòng`);
  };

  const copyItems = async (status: MaterialStatus) => {
    const content = items.filter((item) => item.status === status).map((item) => item.value).join("\n");
    if (!content) return toast.info("Không có dòng nào để copy");
    await navigator.clipboard.writeText(content);
    toast.success(`Đã copy ${status === "OK" ? "dòng OK" : status === "BAD" ? "dòng lỗi" : "dòng mới"}`);
  };

  const copyOne = async (value: string) => {
    await navigator.clipboard.writeText(value);
    toast.success("Đã copy 1 dòng");
  };

  const addOkToStock = async () => {
    const okItems = items.filter((item) => item.status === "OK");
    if (!stockCode || !okItems.length) return;
    const stockKeys = new Set(
      (data?.pool || [])
        .map((row) => materialKey(row.secret))
        .filter(Boolean),
    );
    const seenKeys = new Set<string>();
    const cleanOkItems: MaterialItem[] = [];
    const duplicateOkItems: MaterialItem[] = [];

    okItems.forEach((item) => {
      const key = materialKey(item.value);
      if (stockKeys.has(key) || seenKeys.has(key)) {
        duplicateOkItems.push({ ...item, status: "BAD", note: "TRUNG_KHO" });
        return;
      }
      seenKeys.add(key);
      cleanOkItems.push(item);
    });

    const applyDuplicateFilter = async () => {
      const duplicateById = new Map(duplicateOkItems.map((item) => [item.id, item]));
      const cleanIds = new Set(cleanOkItems.map((item) => item.id));
      const next = items
        .filter((item) => !cleanIds.has(item.id))
        .map((item) => duplicateById.get(item.id) || item);
      setItems(next);
      saveItems(next);
      await saveRemote(next, {
        upsertItems: duplicateOkItems,
        deletedIds: cleanOkItems.map((item) => item.id),
      });
      return next;
    };

    if (!cleanOkItems.length && duplicateOkItems.length) {
      setBusy(true);
      try {
        await applyDuplicateFilter();
        toast.warning(`Không thêm dòng nào. Đã lọc ${duplicateOkItems.length} dòng trùng sang Lỗi.`);
      } finally {
        setBusy(false);
      }
      return;
    }
    setBusy(true);
    try {
      await adminApi("/admin/api/stock", adminKey, {
        method: "POST",
        body: JSON.stringify({ stock_code: stockCode, items: cleanOkItems.map((item) => item.value).join("\n") }),
      });
      await applyDuplicateFilter();
      const duplicateMessage = duplicateOkItems.length ? `, lọc trùng ${duplicateOkItems.length} dòng sang Lỗi` : "";
      toast.success(`Đã thêm ${cleanOkItems.length} dòng OK vào kho ${stockCode}${duplicateMessage}`);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const renderRows = (status: MaterialStatus) => {
    const visible = items.filter((item) => item.status === status);
    const rowClass = status === "OK"
      ? "bg-emerald-50/70 hover:bg-emerald-50"
      : status === "BAD"
        ? "bg-rose-50/70 hover:bg-rose-50"
        : "";
    return (
      <Card className="shadow-sm">
        <CardContent className="p-0">
          <div className="hidden overflow-x-auto md:block">
          <Table className="min-w-[760px]">
            <TableHeader>
              <TableRow>
                <TableHead className="w-[70px]">STT</TableHead>
                <TableHead>Nguyên liệu</TableHead>
                <TableHead className="w-[300px] text-right">Thao tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((item, index) => (
                <TableRow key={item.id} className={rowClass}>
                  <TableCell className="font-mono text-xs text-muted-foreground">{index + 1}</TableCell>
                  <TableCell
                    className="font-mono text-xs max-w-[520px] truncate cursor-pointer select-none active:bg-muted"
                    title="Chạm để copy"
                    onClick={() => copyOne(item.value)}
                  >
                    {item.value}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button size="sm" variant="outline" className="gap-1" onClick={() => copyOne(item.value)}><Copy size={14} /> Copy</Button>
                      <Button size="sm" variant="outline" onClick={() => updateStatus(item.id, "OK")}>OK</Button>
                      <Button size="sm" variant="outline" onClick={() => updateStatus(item.id, "BAD")}>Lỗi</Button>
                      <Button size="sm" variant="ghost" onClick={() => updateStatus(item.id, "NEW")}><RotateCcw size={14} /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {visible.length === 0 && <TableRow><TableCell colSpan={3} className="text-center py-8 text-muted-foreground">Chưa có dữ liệu</TableCell></TableRow>}
            </TableBody>
          </Table>
          </div>

          <div className="md:hidden">
            <div className="grid grid-cols-[48px_minmax(0,1fr)_104px] border-b bg-muted/40 px-3 py-2 text-sm font-medium">
              <div>STT</div>
              <div>Nguyên liệu</div>
              <div className="text-right">Thao tác</div>
            </div>
            {visible.map((item, index) => (
              <div
                key={item.id}
                className={`grid grid-cols-[48px_minmax(0,1fr)_104px] items-center gap-2 border-b px-3 py-2 ${rowClass}`}
              >
                <div className="text-sm text-muted-foreground">{index + 1}</div>
                <button
                  type="button"
                  className="min-w-0 truncate text-left font-mono text-xs leading-8 active:bg-muted"
                  title="Chạm để copy"
                  onClick={() => copyOne(item.value)}
                >
                  {item.value}
                </button>
                <div className="flex justify-end gap-1">
                  <Button size="sm" variant="outline" className="h-8 w-8 px-0 text-xs" onClick={() => updateStatus(item.id, "OK")}>OK</Button>
                  <Button size="sm" variant="outline" className="h-8 w-8 px-0 text-xs" onClick={() => updateStatus(item.id, "BAD")}>Lỗi</Button>
                  <Button size="sm" variant="ghost" className="h-8 w-8 px-0" onClick={() => updateStatus(item.id, "NEW")}><RotateCcw size={14} /></Button>
                </div>
              </div>
            ))}
            {visible.length === 0 && (
              <div className="py-8 text-center text-sm text-muted-foreground">Chưa có dữ liệu</div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2"><Clipboard size={20} /> Nguyên liệu</h2>
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">Mới {counts.NEW}</Badge>
          <Badge variant="default">OK {counts.OK}</Badge>
          <Badge variant="destructive">Lỗi {counts.BAD}</Badge>
        </div>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-4 space-y-3">
          <Textarea
            className="min-h-28 font-mono text-xs"
            placeholder="Dán list nguyên liệu vào đây, mỗi dòng là 1 account/secret..."
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={importRaw} disabled={!raw.trim()}>Thêm vào danh sách</Button>
            <Button variant="outline" className="gap-2" onClick={() => copyItems("OK")}><Copy size={15} /> Copy OK</Button>
            <Button variant="outline" className="gap-2" onClick={() => copyItems("BAD")}><Copy size={15} /> Copy lỗi</Button>
            <Button variant="ghost" className="gap-2" onClick={() => clearStatus("NEW")} disabled={counts.NEW === 0}>
              <Trash2 size={15} /> Xóa chưa phân loại
            </Button>
            <Button variant="ghost" className="gap-2" onClick={() => clearStatus("OK")} disabled={counts.OK === 0}>
              <Trash2 size={15} /> Xóa OK
            </Button>
            <Button variant="ghost" className="gap-2" onClick={() => clearStatus("BAD")} disabled={counts.BAD === 0}>
              <Trash2 size={15} /> Xóa lỗi
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-4 flex flex-wrap items-center gap-2">
          <Select value={stockCode || "__empty"} onValueChange={(value) => setStockCode(value === "__empty" ? "" : value)}>
            <SelectTrigger className="w-56"><SelectValue placeholder="Chọn stock để nhập kho" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__empty">Chọn stock</SelectItem>
              {productCodes.map((code) => <SelectItem key={code} value={code}>{code}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button className="gap-2" onClick={addOkToStock} disabled={busy || !stockCode || counts.OK === 0}>
            <PackageCheck size={16} /> Đẩy OK vào kho bán
          </Button>
          <p className="text-sm text-muted-foreground">Sau khi đẩy vào kho, các dòng OK sẽ tự xóa khỏi danh sách nguyên liệu.</p>
        </CardContent>
      </Card>

      <Tabs defaultValue="NEW">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <TabsList>
            <TabsTrigger value="NEW">Chưa phân loại</TabsTrigger>
            <TabsTrigger value="OK">Dùng được</TabsTrigger>
            <TabsTrigger value="BAD">Không dùng được</TabsTrigger>
          </TabsList>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => bulkUpdateStatus("NEW", "OK")} disabled={counts.NEW === 0}>
              Chuyển chưa phân loại sang OK
            </Button>
            <Button size="sm" variant="outline" onClick={() => bulkUpdateStatus("NEW", "BAD")} disabled={counts.NEW === 0}>
              Chuyển chưa phân loại sang Lỗi
            </Button>
          </div>
        </div>
        <TabsContent value="NEW" className="pt-3">{renderRows("NEW")}</TabsContent>
        <TabsContent value="OK" className="pt-3">{renderRows("OK")}</TabsContent>
        <TabsContent value="BAD" className="pt-3">{renderRows("BAD")}</TabsContent>
      </Tabs>
    </div>
  );
}
