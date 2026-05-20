import { useMemo, useState } from "react";
import { Copy, MailCheck, Search } from "lucide-react";
import { toast } from "sonner";
import { adminApi } from "../../api";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Textarea } from "../ui/textarea";

type CheckStatus = "PLUS" | "OLD_PLUS" | "NO_PLUS_MAIL" | "BANNED" | "ERROR";
type PanelMode = "plus" | "banned" | "other";

type CheckResult = {
  email: string;
  status: CheckStatus;
  label: string;
  error?: string;
  matched?: {
    subject?: string;
    time?: string;
    preview?: string;
  } | null;
};

interface Props {
  adminKey: string;
}

const STORAGE_KEY = "admin_gpt_plus_check_input_v1";
const RESULT_KEY = "admin_gpt_plus_check_results_v1";

const loadText = () => localStorage.getItem(STORAGE_KEY) || "";

function loadResults(): CheckResult[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(RESULT_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function emailFromLine(line: string) {
  return line.split("|", 1)[0].split("----", 1)[0].trim().toLowerCase();
}

export function GptPlusCheck({ adminKey }: Props) {
  const [raw, setRaw] = useState(loadText);
  const [results, setResults] = useState<CheckResult[]>(loadResults);
  const [busy, setBusy] = useState(false);

  const originalByEmail = useMemo(() => {
    const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    return new Map(lines.map((line) => [emailFromLine(line), line]));
  }, [raw]);

  const plusResults = useMemo(() => results.filter((row) => row.status === "PLUS"), [results]);
  const bannedResults = useMemo(() => results.filter((row) => row.status === "BANNED"), [results]);
  const missingResults = useMemo(
    () => results.filter((row) => row.status !== "PLUS" && row.status !== "BANNED"),
    [results],
  );

  const updateRaw = (value: string) => {
    setRaw(value);
    localStorage.setItem(STORAGE_KEY, value);
  };

  const runCheck = async () => {
    const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length) return toast.info("Chưa có mail để check");
    setBusy(true);
    try {
      const response = await adminApi<{ results: CheckResult[] }>("/admin/api/gpt-plus-check", adminKey, {
        method: "POST",
        body: JSON.stringify({ items: lines, limit: 30, active_days: 45 }),
      });
      setResults(response.results || []);
      localStorage.setItem(RESULT_KEY, JSON.stringify(response.results || []));
      toast.success(`Đã check ${response.results?.length || 0} mail`);
    } finally {
      setBusy(false);
    }
  };

  const lineFor = (row: CheckResult) => originalByEmail.get(row.email.toLowerCase()) || row.email;

  const copyRows = async (rows: CheckResult[]) => {
    const content = rows.map(lineFor).join("\n");
    if (!content) return toast.info("Không có dòng để copy");
    await navigator.clipboard.writeText(content);
    toast.success("Đã copy");
  };

  const copyOne = async (row: CheckResult) => {
    await navigator.clipboard.writeText(lineFor(row));
    toast.success("Đã copy 1 dòng");
  };

  const clearAll = () => {
    setResults([]);
    setRaw("");
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(RESULT_KEY);
  };

  const resultPanel = (title: string, rows: CheckResult[], mode: PanelMode) => {
    const isPlus = mode === "plus";
    const isBanned = mode === "banned";
    return (
      <Card className="shadow-sm">
        <CardContent className="p-0">
          <div className="flex items-center justify-between gap-2 border-b px-4 py-3">
            <div className="font-medium">{title}</div>
            <Button
              size="sm"
              variant={isPlus ? "default" : "outline"}
              className={isBanned ? "gap-2 border-red-200 text-red-700 hover:bg-red-50" : "gap-2"}
              onClick={() => copyRows(rows)}
            >
              <Copy size={14} /> Copy tất cả
            </Button>
          </div>
          <div className="max-h-[560px] overflow-y-auto">
            {rows.map((row, index) => (
              <button
                key={`${row.email}-${index}`}
                type="button"
                className="grid w-full grid-cols-[40px_minmax(0,1fr)_86px] items-center gap-2 border-b px-4 py-2 text-left hover:bg-muted/60 active:bg-muted"
                title={row.error || row.matched?.subject || row.matched?.preview || "Bấm để copy"}
                onClick={() => copyOne(row)}
              >
                <span className="text-sm text-muted-foreground">{index + 1}</span>
                <span className="min-w-0">
                  <span className="block truncate font-mono text-xs">{row.email}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {row.error || row.matched?.subject || row.matched?.preview || row.label}
                  </span>
                </span>
                <Badge
                  className={isPlus ? "bg-emerald-600" : isBanned ? "bg-red-600" : ""}
                  variant={isPlus || isBanned ? "default" : "outline"}
                >
                  {isPlus ? "Có" : isBanned ? "Die" : "Chưa"}
                </Badge>
              </button>
            ))}
            {rows.length === 0 && (
              <div className="py-10 text-center text-sm text-muted-foreground">Chưa có dữ liệu</div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2"><MailCheck size={20} /> Check GPT Plus</h2>
        <div className="flex flex-wrap gap-2">
          <Badge className="bg-emerald-600">Có {plusResults.length}</Badge>
          <Badge className="bg-red-600">Die {bannedResults.length}</Badge>
          <Badge variant="outline">Chưa {missingResults.length}</Badge>
        </div>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-4 space-y-3">
          <Textarea
            className="h-11 min-h-11 resize-none overflow-hidden whitespace-nowrap font-mono text-xs"
            placeholder="Dán list email|refresh_token|client_id..."
            value={raw}
            onChange={(event) => updateRaw(event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button className="gap-2" onClick={runCheck} disabled={busy || !raw.trim()}>
              <Search size={15} /> {busy ? "Đang check..." : "Check GPT Plus"}
            </Button>
            <Button variant="ghost" onClick={clearAll}>Xóa</Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {resultPanel(`Có gói (${plusResults.length})`, plusResults, "plus")}
        {resultPanel(`Acc die / bị ban (${bannedResults.length})`, bannedResults, "banned")}
        {resultPanel(`Chưa có / lỗi (${missingResults.length})`, missingResults, "other")}
      </div>
    </div>
  );
}
