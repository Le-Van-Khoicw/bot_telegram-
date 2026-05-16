import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { AdminLogin } from "./components/AdminLogin";
import { Sidebar, type AdminSection } from "./components/Sidebar";
import { Overview } from "./components/sections/Overview";
import { Products } from "./components/sections/Products";
import { Inventory } from "./components/sections/Inventory";
import { Orders } from "./components/sections/Orders";
import { Users } from "./components/sections/Users";
import { Reservations } from "./components/sections/Reservations";
import { Fulfillments } from "./components/sections/Fulfillments";
import { Button } from "./components/ui/button";
import { adminApi, type AdminSnapshot } from "./api";

export default function App() {
  const [adminKey, setAdminKey] = useState(() => sessionStorage.getItem("admin_key") || "");
  const [section, setSection] = useState<AdminSection>("overview");
  const [data, setData] = useState<AdminSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const isAuthenticated = Boolean(adminKey);

  const refresh = async (key = adminKey) => {
    if (!key) return;
    setLoading(true);
    setMessage("Đang tải dữ liệu...");
    try {
      const next = await adminApi<AdminSnapshot>("/admin/api/snapshot?limit=300", key);
      setData(next);
      setMessage(`Cập nhật lúc ${next.generated_at} (${next.timezone})`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Không tải được dữ liệu");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (adminKey) refresh(adminKey).catch(() => undefined);
  }, []);

  const handleLogin = async (key: string) => {
    await adminApi("/admin/api/login", key);
    sessionStorage.setItem("admin_key", key);
    setAdminKey(key);
    await refresh(key);
  };

  const handleLogout = () => {
    sessionStorage.removeItem("admin_key");
    setAdminKey("");
    setData(null);
  };

  if (!isAuthenticated) {
    return <AdminLogin onLogin={handleLogin} />;
  }

  const common = { data, adminKey, refresh };
  const renderSection = () => {
    switch (section) {
      case "overview": return <Overview data={data} />;
      case "products": return <Products {...common} />;
      case "inventory": return <Inventory {...common} />;
      case "orders": return <Orders {...common} />;
      case "users": return <Users data={data} />;
      case "reservations": return <Reservations data={data} />;
      case "fulfillments": return <Fulfillments data={data} />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar active={section} onChange={setSection} onLogout={handleLogout} />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 py-6 pt-16 md:pt-6">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Khoi Van Store Admin</h1>
              <p className="text-xs text-muted-foreground">{message || "Sẵn sàng quản lý bot bán hàng"}</p>
            </div>
            <Button size="sm" variant="outline" className="gap-2 self-start sm:self-auto" onClick={() => refresh()} disabled={loading}>
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
              Làm mới
            </Button>
          </div>
          {renderSection()}
        </div>
      </main>
    </div>
  );
}
