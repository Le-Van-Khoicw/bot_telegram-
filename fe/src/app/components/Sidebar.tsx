import { LayoutDashboard, Package, Warehouse, ClipboardList, Users, BookMarked, Truck, LogOut, Menu, X, ClipboardCheck, MailCheck } from "lucide-react";
import { Button } from "./ui/button";
import { type ReactNode, useState } from "react";

export type AdminSection =
  | "overview"
  | "products"
  | "inventory"
  | "materials"
  | "gptPlus"
  | "orders"
  | "users"
  | "reservations"
  | "fulfillments";

export const NAV_ITEMS: { id: AdminSection; label: string; icon: ReactNode }[] = [
  { id: "overview", label: "Tổng quan", icon: <LayoutDashboard size={18} /> },
  { id: "products", label: "Sản phẩm", icon: <Package size={18} /> },
  { id: "inventory", label: "Kho hàng", icon: <Warehouse size={18} /> },
  { id: "materials", label: "Nguyên liệu", icon: <ClipboardCheck size={18} /> },
  { id: "gptPlus", label: "Check GPT Plus", icon: <MailCheck size={18} /> },
  { id: "orders", label: "Đơn hàng", icon: <ClipboardList size={18} /> },
  { id: "users", label: "Khách hàng", icon: <Users size={18} /> },
  { id: "reservations", label: "Giữ hàng", icon: <BookMarked size={18} /> },
  { id: "fulfillments", label: "Giao hàng", icon: <Truck size={18} /> },
];

interface SidebarProps {
  active: AdminSection;
  onChange: (s: AdminSection) => void;
  onLogout: () => void;
}

export function Sidebar({ active, onChange, onLogout }: SidebarProps) {
  const [open, setOpen] = useState(false);

  const navContent = (
    <nav className="flex flex-col h-full">
      <div className="px-4 py-4 border-b border-border">
        <p className="text-sm font-semibold">Admin Panel</p>
        <p className="text-xs text-muted-foreground truncate">bot-telegram-1-mgsf</p>
      </div>

      <div className="flex-1 py-3 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => { onChange(item.id); setOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
              active === item.id
                ? "bg-emerald-600 text-white"
                : "text-muted-foreground hover:bg-emerald-50 hover:text-emerald-700"
            }`}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>

      <div className="p-3 border-t border-border">
        <Button variant="ghost" size="sm" className="w-full gap-2 justify-start" onClick={onLogout}>
          <LogOut size={16} />
          Đăng xuất
        </Button>
      </div>
    </nav>
  );

  return (
    <>
      <aside className="hidden md:flex flex-col w-56 bg-white border-r border-border flex-shrink-0 h-screen sticky top-0">
        {navContent}
      </aside>

      <div className="md:hidden fixed top-3 left-3 z-50">
        <Button variant="outline" size="icon" onClick={() => setOpen((v) => !v)}>
          {open ? <X size={18} /> : <Menu size={18} />}
        </Button>
      </div>

      {open && (
        <div className="md:hidden fixed inset-0 z-40 flex">
          <div className="w-[82vw] max-w-xs bg-white h-full shadow-xl">{navContent}</div>
          <div className="flex-1 bg-black/30" onClick={() => setOpen(false)} />
        </div>
      )}
    </>
  );
}
