"use client";

import * as React from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import {
  LogOut,
  User as UserIcon,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { useSession } from "@/components/session-provider";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";

export function Topbar() {
  const { user, loading } = useSession();
  const router = useRouter();
  const [logoutLoading, setLogoutLoading] = React.useState(false);

  const initials = user
    ? user.name
        .split(" ")
        .slice(0, 2)
        .map((p) => p[0]?.toUpperCase())
        .join("")
    : "?";

  const onLogout = async () => {
    setLogoutLoading(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      toast.success("Logged out");
      router.push("/login");
      router.refresh();
    } finally {
      setLogoutLoading(false);
    }
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-background/60 px-4 backdrop-blur-xl lg:px-8">
      <div className="flex items-center gap-2 text-sm text-muted-foreground lg:hidden">
        <Sparkles className="h-4 w-4 text-primary" />
        <span className="font-semibold text-foreground">Job Booster</span>
      </div>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        <Button
          variant="outline"
          size="sm"
          className="hidden gap-2 sm:flex"
          onClick={() => router.push("/apply")}
        >
          <Sparkles className="h-3.5 w-3.5" />
          Quick Apply
        </Button>

        <Link
          href="/onboarding"
          className="hidden items-center gap-1.5 rounded-md border border-border bg-secondary/40 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground sm:flex"
        >
          <span className="relative flex h-1.5 w-1.5">
            <span
              className={`absolute inline-flex h-full w-full rounded-full ${
                user?.hasPersonalContext ? "bg-emerald-400" : "bg-amber-400 animate-ping"
              } opacity-75`}
            />
            <span
              className={`relative inline-flex h-1.5 w-1.5 rounded-full ${
                user?.hasPersonalContext ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
          </span>
          {loading
            ? "Checking profile…"
            : user?.hasPersonalContext
              ? "Onboarding done"
              : "Complete onboarding"}
          <ChevronRight className="h-3 w-3" />
        </Link>

        {!user?.hasPersonalContext && !loading && (
          <Badge variant="warning" className="hidden md:inline-flex">
            Personalize recs
          </Badge>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full">
              <Avatar>
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span className="text-sm font-medium">{user?.name ?? "Guest"}</span>
                <span className="text-xs text-muted-foreground">{user?.email ?? ""}</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/account">
                <UserIcon />
                Account
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/onboarding">
                <Sparkles />
                Onboarding
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={onLogout}
              disabled={logoutLoading}
              className="text-destructive focus:text-destructive"
            >
              <LogOut />
              {logoutLoading ? "Logging out…" : "Log out"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
