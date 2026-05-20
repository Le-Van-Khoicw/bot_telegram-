import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, RefreshCw } from "lucide-react";
import { toast, Toaster } from "sonner";
import { AdminLogin } from "./components/AdminLogin";
import { NAV_ITEMS, Sidebar, type AdminSection } from "./components/Sidebar";
import { NotificationPanel, type Notification } from "./components/NotificationPanel";
import { Overview } from "./components/sections/Overview";
import { Products } from "./components/sections/Products";
import { Inventory } from "./components/sections/Inventory";
import { Materials } from "./components/sections/Materials";
import { GptPlusCheck } from "./components/sections/GptPlusCheck";
import { Orders } from "./components/sections/Orders";
import { Users } from "./components/sections/Users";
import { Reservations } from "./components/sections/Reservations";
import { Fulfillments } from "./components/sections/Fulfillments";
import { Button } from "./components/ui/button";
import { adminApi, money, text, type AdminSnapshot } from "./api";
import { clearToken, getToken, saveToken } from "./utils/auth";

const POLL_MS = 60_000;

export default function App() {
  const [adminKey, setAdminKey] = useState(() => getToken() || "");
  const [section, setSection] = useState<AdminSection>("overview");
  const [data, setData] = useState<AdminSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [newCount, setNewCount] = useState(0);
  const [inventoryPreset, setInventoryPreset] = useState<{ status?: string; stockCode?: string; nonce: number }>({ nonce: 0 });
  const [orderPreset, setOrderPreset] = useState<{ status?: string; nonce: number }>({ nonce: 0 });

  // ✅ NEW: Notification management
  const [notifications, setNotifications] = useState<Notification[]>(() => {
    try {
      const saved = localStorage.getItem("notifications");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [notifPanelOpen, setNotifPanelOpen] = useState(false);

  const seenOrdersRef = useRef<Set<string>>(new Set());
  const deliveredRef = useRef<Set<string>>(new Set());
  const initializedRef = useRef(false);
  const audioRef = useRef<AudioContext | null>(null);

  const isAuthenticated = Boolean(adminKey);

  const playNotifySound = useCallback(() => {
    try {
      const Ctx = window.AudioContext || (window as any).webkitAudioContext;
      if (!Ctx) return;
      const ctx = audioRef.current || new Ctx();
      audioRef.current = ctx;
      if (ctx.state === "suspended") void ctx.resume();

      const oscillator = ctx.createOscillator();
      const gain = ctx.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = 880;
      gain.gain.setValueAtTime(0.001, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.12, ctx.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.22);
      oscillator.connect(gain);
      gain.connect(ctx.destination);
      oscillator.start();
      oscillator.stop(ctx.currentTime + 0.24);
    } catch {
      // Browser may block audio until the page has a user gesture.
    }
  }, []);

  const notifyFromSnapshot = useCallback((next: AdminSnapshot) => {
    const nextIds = new Set<string>();
    const nextDelivered = new Set<string>();
    const newOrders: any[] = [];
    const deliveredOrders: any[] = [];

    for (const order of next.orders || []) {
      const id = text(order.order_id);
      if (id === "—") continue;
      nextIds.add(id);
      if (!seenOrdersRef.current.has(id)) newOrders.push(order);
      if (text(order.status).toUpperCase() === "DELIVERED") {
        nextDelivered.add(id);
        if (!deliveredRef.current.has(id)) deliveredOrders.push(order);
      }
    }

    if (initializedRef.current) {
      const newNotifications: Notification[] = [];

      if (newOrders.length) {
        setNewCount((n) => n + newOrders.length);
        playNotifySound();
        const first = newOrders[0];
        toast.success(`Có ${newOrders.length} đơn mới`, {
          description: `${text(first.stock_code)} - ${money(first.total)} - ${text(first.order_id)}`,
          duration: 7000,
        });

        // ✅ Add to notifications
        for (const order of newOrders) {
          newNotifications.push({
            id: `notif-${Date.now()}-${Math.random()}`,
            type: "new_order",
            orderId: text(order.order_id),
            stockCode: text(order.stock_code),
            total: parseInt(text(order.total)) || 0,
            userId: text(order.user_id),
            createdAt: text(order.created_at),
            timestamp: Date.now(),
          });
        }
      }

      if (deliveredOrders.length) {
        setNewCount((n) => n + deliveredOrders.length);
        playNotifySound();
        const first = deliveredOrders[0];
        toast(`Đã giao ${deliveredOrders.length} đơn`, {
          description: `${text(first.stock_code)} - ${money(first.total)} - ${text(first.order_id)}`,
          duration: 7000,
        });

        // ✅ Add to notifications
        for (const order of deliveredOrders) {
          newNotifications.push({
            id: `notif-${Date.now()}-${Math.random()}`,
            type: "delivered",
            orderId: text(order.order_id),
            stockCode: text(order.stock_code),
            total: parseInt(text(order.total)) || 0,
            userId: text(order.user_id),
            createdAt: text(order.created_at),
            timestamp: Date.now(),
          });
        }
      }

      // ✅ Update notifications state and localStorage
      if (newNotifications.length) {
        setNotifications((prev) => {
          const updated = [...newNotifications, ...prev].slice(0, 100); // Keep max 100
          localStorage.setItem("notifications", JSON.stringify(updated));
          return updated;
        });
      }
    }

    seenOrdersRef.current = nextIds;
    deliveredRef.current = nextDelivered;
    initializedRef.current = true;
  }, [playNotifySound]);

  const refresh = useCallback(async (key = adminKey, options: { silent?: boolean } = {}) => {
    if (!key) return;
    if (!options.silent) {
      setLoading(true);
      setMessage("Đang tải dữ liệu...");
    }
    try {
      const next = await adminApi<AdminSnapshot>("/admin/api/snapshot?limit=300&pool_limit=20000", key);
      notifyFromSnapshot(next);
      setData(next);
      setMessage(`Cập nhật lúc ${next.generated_at} (${next.timezone})`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Không tải được dữ liệu";
      if (errorMessage.toLowerCase().includes("unauthorized")) {
        clearToken();
        setAdminKey("");
        setData(null);
        initializedRef.current = false;
      }
      if (!options.silent) {
        setMessage(errorMessage);
      }
      throw err;
    } finally {
      if (!options.silent) setLoading(false);
    }
  }, [adminKey, notifyFromSnapshot]);

  useEffect(() => {
    if (adminKey) refresh(adminKey).catch(() => undefined);
  }, [adminKey, refresh]);

  useEffect(() => {
    if (!adminKey) return;
    const timer = window.setInterval(() => {
      refresh(adminKey, { silent: true }).catch(() => undefined);
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [adminKey, refresh]);

  useEffect(() => {
    document.title = newCount ? `(${newCount}) Khoi Van Store Admin` : "Khoi Van Store Admin";
  }, [newCount]);

  const handleLogin = async (key: string) => {
    await adminApi("/admin/api/login", key);
    saveToken(key);
    setAdminKey(key);
    setNewCount(0);
  };

  const handleLogout = () => {
    clearToken();
    setAdminKey("");
    setData(null);
    setNewCount(0);
    initializedRef.current = false;
    seenOrdersRef.current = new Set();
    deliveredRef.current = new Set();
  };

  // ✅ NEW: Handle notification selection
  const handleSelectNotification = (orderId: string) => {
    setOrderPreset({ status: undefined, nonce: Date.now() });
    setSection("orders");
    // Scroll to selected order (optional, can be improved)
    setTimeout(() => {
      const orderElement = document.getElementById(`order-${orderId}`);
      if (orderElement) {
        orderElement.scrollIntoView({ behavior: "smooth", block: "center" });
        orderElement.classList.add("bg-yellow-100");
        setTimeout(() => orderElement.classList.remove("bg-yellow-100"), 2000);
      }
    }, 100);
  };

  if (!isAuthenticated) {
    return <AdminLogin onLogin={handleLogin} />;
  }

  const common = { data, adminKey, refresh };
  const renderSection = () => {
    switch (section) {
      case "overview": return (
        <Overview
          data={data}
          onOpenOrders={(status) => {
            setOrderPreset({ status, nonce: Date.now() });
            setSection("orders");
          }}
          onOpenInventory={(status, stockCode) => {
            setInventoryPreset({ status, stockCode, nonce: Date.now() });
            setSection("inventory");
          }}
          onOpenUsers={() => setSection("users")}
        />
      );
      case "products": return <Products {...common} />;
      case "inventory": return <Inventory {...common} preset={inventoryPreset} />;
      case "materials": return <Materials {...common} />;
      case "gptPlus": return <GptPlusCheck adminKey={adminKey} refresh={refresh} />;
      case "orders": return <Orders {...common} preset={orderPreset} />;
      case "users": return <Users data={data} />;
      case "reservations": return <Reservations data={data} />;
      case "fulfillments": return <Fulfillments data={data} />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Toaster richColors position="top-right" />
      {/* ✅ NEW: Notification Panel */}
      <NotificationPanel
        notifications={notifications}
        open={notifPanelOpen}
        onClose={() => setNotifPanelOpen(false)}
        onSelectOrder={handleSelectNotification}
        newCount={newCount}
      />
      <Sidebar active={section} onChange={(next) => { setSection(next); setNewCount(0); }} onLogout={handleLogout} />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 py-6 pt-16 md:pt-6">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Khoi Van Store Admin</h1>
              <p className="text-xs text-muted-foreground">{message || "Sẵn sàng quản lý bot bán hàng"}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {newCount > 0 && (
                <Button size="sm" variant="secondary" className="gap-2 relative" onClick={() => setNotifPanelOpen(true)}>
                  <Bell size={15} />
                  {newCount} thông báo mới
                  {newCount > 0 && (
                    <span className="absolute top-0 right-0 -mt-1 -mr-1 w-4 h-4 bg-red-600 text-white text-xs font-bold rounded-full flex items-center justify-center">
                      {newCount > 9 ? "9+" : newCount}
                    </span>
                  )}
                </Button>
              )}
              <Button size="sm" variant="outline" className="gap-2" onClick={() => refresh()} disabled={loading}>
                <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
                Làm mới
              </Button>
            </div>
          </div>
          <div className="mb-4 md:hidden">
            <select
              className="w-full h-11 rounded-md border border-border bg-white px-3 text-sm font-medium shadow-sm"
              value={section}
              onChange={(event) => {
                setSection(event.target.value as AdminSection);
                setNewCount(0);
              }}
            >
              {NAV_ITEMS.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </div>
          {renderSection()}
        </div>
      </main>
    </div>
  );
}
