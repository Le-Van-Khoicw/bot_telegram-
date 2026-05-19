import { useMemo, useState } from "react";
import { Copy, MailCheck, Search } from "lucide-react";
import { toast } from "sonner";
import { adminApi } from "../../api";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Textarea } from "../ui/textarea";

type CheckStatus = "PLUS" | "OLD_PLUS" | "NO_PLUS_MAIL" | "ERROR";

type CheckResult = {
  email: string;
  status: CheckStatus;
  label: string;
  error?: string;
  matched?: {
    from?: string;
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

function loadText() {
  return localStorage.getItem(STORAGE_KEY) || "";
}

function loadResults(): CheckResult[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(RESULT_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function GptPlusCheck({ adminKey }: Props) {
  const [raw, setRaw] = useState(loadText);
  const [results, setResults] = useState<CheckResult[]>(loadResults);
  const [busy, setBusy] = useState(false);

  const counts = useMemo(() => ({
    PLUS: results.filter((row) => row.status === "PLUS").length,
    OLD_PLUS: results.filter((row) => row.status === "OLD_PLUS").length,
    NO_PLUS_MAIL: results.filter((row) => row.status === "NO_PLUS_MAIL").length,
    ERROR: results.filter((row) => row.status === "ERROR").length,
  }), [results]);

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

  const copyByStatus = async (statuses: CheckStatus[]) => {
    const originalLines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const byEmail = new Map(originalLines.map((line) => [
      line.split("|", 1)[0].split("----", 1)[0].trim().toLowerCase(),
      line,
    ]));
    const content = results
      .filter((row) => statuses.includes(row.status))
      .map((row) => byEmail.get(row.email.toLowerCase()) || row.email)
      .join("\n");
    if (!content) return toast.info("Không có dòng để copy");
    await navigator.clipboard.writeText(content);
    toast.success("Đã copy");
  };

  const clearAll = () => {
    setResults([]);
    setRaw("");
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(RESULT_KEY);
  };

  const statusBadge = (status: CheckStatus) => {
    if (status === "PLUS") return <Badge className="bg-emerald-600">Có gói</Badge>;
    if (status === "OLD_PLUS") return <Badge variant="secondary">Mail cũ</Badge>;
    if (status === "ERROR") return <Badge variant="destructive">Lỗi</Badge>;
    return <Badge variant="outline">Không thấy</Badge>;
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2"><MailCheck size={20} /> Check GPT Plus</h2>
        <div className="flex flex-wrap gap-2">
          <Badge className="bg-emerald-600">Plus {counts.PLUS}</Badge>
          <Badge variant="secondary">Cũ {counts.OLD_PLUS}</Badge>
          <Badge variant="outline">Không thấy {counts.NO_PLUS_MAIL}</Badge>
          <Badge variant="destructive">Lỗi {counts.ERROR}</Badge>
        </div>
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-4 space-y-3">
          <Textarea
            className="min-h-36 font-mono text-xs"
            placeholder="Dán list dạng email|refresh_token|client_id, mỗi dòng 1 mail..."
            value={raw}
            onChange={(event) => updateRaw(event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button className="gap-2" onClick={runCheck} disabled={busy || !raw.trim()}>
              <Search size={15} /> {busy ? "Đang check..." : "Check GPT Plus"}
            </Button>
            <Button variant="outline" className="gap-2" onClick={() => copyByStatus(["PLUS"])}>
              <Copy size={15} /> Copy có gói
            </Button>
            <Button variant="outline" className="gap-2" onClick={() => copyByStatus(["NO_PLUS_MAIL", "ERROR"])}>
              <Copy size={15} /> Copy lỗi/không thấy
            </Button>
            <Button variant="ghost" onClick={clearAll}>Xóa</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-0 overflow-x-auto">
          <Table className="min-w-[860px]">
            <TableHeader>
              <TableRow>
                <TableHead className="w-[56px]">#</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="w-[130px]">Trạng thái</TableHead>
                <TableHead>Mail khớp</TableHead>
                <TableHead className="w-[180px]">Thời gian</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((row, index) => (
                <TableRow key={`${row.email}-${index}`}>
                  <TableCell className="text-muted-foreground">{index + 1}</TableCell>
                  <TableCell className="font-mono text-xs">{row.email}</TableCell>
                  <TableCell>{statusBadge(row.status)}</TableCell>
                  <TableCell className="max-w-[360px] truncate" title={row.error || row.matched?.subject || ""}>
                    {row.error || row.matched?.subject || "—"}
                  </TableCell>
                  <TableCell>{row.matched?.time || "—"}</TableCell>
                </TableRow>
              ))}
              {results.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">Chưa có kết quả</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
