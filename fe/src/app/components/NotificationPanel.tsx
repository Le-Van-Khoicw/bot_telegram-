import { X, Bell } from "lucide-react";
import { Button } from "./ui/button";
import { money, text, type AdminSnapshot } from "../api";

export interface Notification {
  id: string;
  type: "new_order" | "delivered";
  orderId: string;
  stockCode: string;
  total: number;
  userId: string;
  createdAt: string;
  timestamp: number;
}

interface NotificationPanelProps {
  notifications: Notification[];
  open: boolean;
  onClose: () => void;
  onSelectOrder: (orderId: string) => void;
  newCount: number;
}

export function NotificationPanel({
  notifications,
  open,
  onClose,
  onSelectOrder,
  newCount,
}: NotificationPanelProps) {
  if (!open) return null;

  const sorted = [...notifications].sort((a, b) => b.timestamp - a.timestamp);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-md h-screen md:h-auto md:max-h-[80vh] bg-white shadow-lg rounded-lg md:rounded-l-lg flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <Bell size={18} className="text-blue-600" />
            <h2 className="font-semibold">Thông báo</h2>
            {newCount > 0 && (
              <span className="ml-2 inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-600 rounded-full">
                {newCount > 99 ? "99+" : newCount}
              </span>
            )}
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X size={16} />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {sorted.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-center text-muted-foreground">
              <Bell size={32} className="mb-2 opacity-20" />
              <p>Không có thông báo nào</p>
            </div>
          ) : (
            <div className="divide-y">
              {sorted.map((notif) => (
                <div
                  key={notif.id}
                  className="p-4 hover:bg-slate-50 cursor-pointer transition-colors"
                  onClick={() => {
                    onSelectOrder(notif.orderId);
                    onClose();
                  }}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`flex-shrink-0 w-2 h-2 rounded-full mt-1.5 ${notif.type === "new_order"
                          ? "bg-blue-600"
                          : "bg-green-600"
                        }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`text-xs font-semibold px-2 py-0.5 rounded ${notif.type === "new_order"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-green-100 text-green-700"
                            }`}
                        >
                          {notif.type === "new_order" ? "📦 Đơn mới" : "✅ Đã giao"}
                        </span>
                      </div>
                      <div className="text-sm font-medium text-slate-900 truncate">
                        {notif.stockCode}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Mã: <span className="font-mono">{notif.orderId}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Khách: {notif.userId}
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-sm font-semibold text-slate-900">
                          {money(notif.total)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(notif.timestamp).toLocaleTimeString("vi-VN", {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {sorted.length > 0 && (
          <div className="border-t px-4 py-2">
            <Button
              size="sm"
              variant="ghost"
              className="w-full text-xs text-muted-foreground"
              onClick={() => {
                localStorage.setItem("notifications", JSON.stringify([]));
                onClose();
                window.location.reload();
              }}
            >
              Xóa tất cả
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
