"use client";

import { User, Shield, LogOut, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSession } from "@/components/session-provider";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import * as React from "react";

export default function AccountPage() {
  const { user, loading, refresh } = useSession();
  const router = useRouter();
  const [logoutLoading, setLogoutLoading] = React.useState(false);

  const onLogout = async () => {
    setLogoutLoading(true);
    await fetch("/api/auth/logout", { method: "POST" });
    toast.success("Logged out");
    router.push("/login");
    router.refresh();
    setLogoutLoading(false);
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Account" description="Your profile and session" icon={User} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Row label="Name" value={loading ? "…" : user?.name} />
            <Row label="Email" value={loading ? "…" : user?.email} />
            <Row label="User ID" value={loading ? "…" : user?.id?.toString()} />
            <div className="flex items-center justify-between border-t border-border pt-3">
              <span className="text-sm text-muted-foreground">Onboarding status</span>
              {user?.hasPersonalContext ? (
                <Badge variant="success">Complete</Badge>
              ) : (
                <Badge variant="warning">Pending</Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Shield className="h-4 w-4 text-primary" /> Session
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-muted-foreground">
              JWT stored in an HttpOnly cookie. Session refreshes automatically.
            </p>
            <div className="flex flex-col gap-2">
              <Button variant="outline" size="sm" onClick={() => refresh()} className="gap-1.5">
                Refresh session
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onLogout}
                disabled={logoutLoading}
                className="gap-1.5 text-destructive hover:text-destructive"
              >
                {logoutLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <LogOut className="h-3.5 w-3.5" />}
                Log out
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value ?? "—"}</span>
    </div>
  );
}
