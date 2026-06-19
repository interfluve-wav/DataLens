import {
  BarChart3,
  Columns3,
  FileText,
  Gauge,
  GitCompare,
  LayoutDashboard,
  Network,
  Wrench,
  Upload,
  LogOut,
} from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { useDataLens } from "@/context/DataLensContext"
import { DASHBOARDS, type DashboardId } from "@/types/datalens"
import { qualityLabel, effectiveQualityScore } from "@/lib/quality"
import { DashboardRouter } from "@/components/layout/DashboardRouter"
import { RowSampleSelect } from "@/components/layout/RowSampleSelect"
import { LoadingOverlay } from "@/components/layout/LoadingOverlay"

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  gauge: Gauge,
  grid: Columns3,
  chart: BarChart3,
  "layout-dashboard": LayoutDashboard,
  wrench: Wrench,
  "git-compare": GitCompare,
  network: Network,
  "file-text": FileText,
}

const SIDEBAR_GROUPS: { label: string; ids: DashboardId[] }[] = [
  { label: "Summary", ids: ["overview"] },
  {
    label: "Explore",
    ids: ["columns", "distributions", "analytics", "correlation"],
  },
  { label: "Act", ids: ["recommendations", "drift", "report"] },
]

export function AppShell() {
  const { data, activeDashboard, setActiveDashboard, clear } = useDataLens()

  if (!data) return null

  const effective = effectiveQualityScore(data)

  return (
    <SidebarProvider>
      <LoadingOverlay />
      <Sidebar variant="inset" className="border-r border-sidebar-border">
        <SidebarHeader className="gap-3 border-b border-sidebar-border p-4">
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary font-bold text-sm text-primary-foreground">
              DL
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold leading-none">DataLens</p>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {data.filename}
                {data.sheet_name ? ` · ${data.sheet_name}` : ""}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="secondary" className="tabular-nums">
              {effective.overall.toFixed(1)}
            </Badge>
            <Badge variant="outline" className="text-xs">
              {qualityLabel(effective.level)}
            </Badge>
            {data.profile_assessment && data.quality_profile_id !== "generic" && (
              <Badge variant="outline" className="text-xs">
                {data.profile_assessment.profile_label}
              </Badge>
            )}
          </div>
        </SidebarHeader>
        <SidebarContent className="gap-0">
          {SIDEBAR_GROUPS.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.ids.map((id) => {
                    const d = DASHBOARDS.find((x) => x.id === id)!
                    const Icon = ICONS[d.icon] ?? Gauge
                    return (
                      <SidebarMenuItem key={d.id}>
                        <SidebarMenuButton
                          isActive={activeDashboard === d.id}
                          onClick={() => setActiveDashboard(d.id)}
                          tooltip={d.description}
                        >
                          <Icon />
                          <span>{d.label}</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    )
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))}
        </SidebarContent>
        <SidebarFooter className="border-t border-sidebar-border p-4">
          <Button variant="outline" size="sm" className="w-full" onClick={clear}>
            <LogOut data-icon="inline-start" />
            New upload
          </Button>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset className="mesh-bg">
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b border-border/50 bg-background/70 px-4 backdrop-blur-md">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-4" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {DASHBOARDS.find((d) => d.id === activeDashboard)?.label}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <RowSampleSelect />
            <Badge variant="outline" className="hidden tabular-nums md:inline-flex">
              {(data.total_row_count ?? data.row_count).toLocaleString()} rows
            </Badge>
            <Button variant="ghost" size="icon-sm" onClick={clear} title="New upload">
              <Upload />
            </Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 overflow-auto p-4 md:p-6 lg:p-8">
          <DashboardRouter />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
