import { lazy, Suspense } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Loader2 } from "lucide-react"
import { useDataLens } from "@/context/DataLensContext"
import type { DashboardId, UploadResponse } from "@/types/datalens"

const OverviewDashboard = lazy(() =>
  import("@/components/dashboards/OverviewDashboard").then((m) => ({
    default: m.OverviewDashboard,
  })),
)
const ColumnsDashboard = lazy(() =>
  import("@/components/dashboards/ColumnsDashboard").then((m) => ({
    default: m.ColumnsDashboard,
  })),
)
const DistributionsDashboard = lazy(() =>
  import("@/components/dashboards/DistributionsDashboard").then((m) => ({
    default: m.DistributionsDashboard,
  })),
)
const RecommendationsDashboard = lazy(() =>
  import("@/components/dashboards/RecommendationsDashboard").then((m) => ({
    default: m.RecommendationsDashboard,
  })),
)
const DriftDashboard = lazy(() =>
  import("@/components/dashboards/DriftDashboard").then((m) => ({
    default: m.DriftDashboard,
  })),
)
const CorrelationDashboard = lazy(() =>
  import("@/components/dashboards/CorrelationDashboard").then((m) => ({
    default: m.CorrelationDashboard,
  })),
)
const AnalyticsDashboard = lazy(() =>
  import("@/components/dashboards/AnalyticsDashboard").then((m) => ({
    default: m.AnalyticsDashboard,
  })),
)
const ReportDashboard = lazy(() =>
  import("@/components/dashboards/ReportDashboard").then((m) => ({
    default: m.ReportDashboard,
  })),
)

const DASHBOARD_COMPONENTS: Record<
  DashboardId,
  React.ComponentType<{ data: UploadResponse }>
> = {
  overview: OverviewDashboard,
  columns: ColumnsDashboard,
  distributions: DistributionsDashboard,
  analytics: AnalyticsDashboard,
  recommendations: RecommendationsDashboard,
  drift: DriftDashboard,
  correlation: CorrelationDashboard,
  report: ReportDashboard,
}

function DashboardFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Loader2 className="size-6 animate-spin text-muted-foreground" />
    </div>
  )
}

export function DashboardRouter() {
  const { data, activeDashboard } = useDataLens()
  if (!data) return null

  const Dashboard = DASHBOARD_COMPONENTS[activeDashboard]

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeDashboard}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
      >
        <Suspense fallback={<DashboardFallback />}>
          <Dashboard data={data} />
        </Suspense>
      </motion.div>
    </AnimatePresence>
  )
}
