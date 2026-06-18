import { AnimatePresence, motion } from "motion/react"
import { useDataLens } from "@/context/DataLensContext"
import { OverviewDashboard } from "@/components/dashboards/OverviewDashboard"
import { ColumnsDashboard } from "@/components/dashboards/ColumnsDashboard"
import { DistributionsDashboard } from "@/components/dashboards/DistributionsDashboard"
import { RecommendationsDashboard } from "@/components/dashboards/RecommendationsDashboard"
import { DriftDashboard } from "@/components/dashboards/DriftDashboard"
import { CorrelationDashboard } from "@/components/dashboards/CorrelationDashboard"
import { AnalyticsDashboard } from "@/components/dashboards/AnalyticsDashboard"
import { ReportDashboard } from "@/components/dashboards/ReportDashboard"

export function DashboardRouter() {
  const { data, activeDashboard } = useDataLens()
  if (!data) return null

  const views = {
    overview: <OverviewDashboard data={data} />,
    columns: <ColumnsDashboard data={data} />,
    distributions: <DistributionsDashboard data={data} />,
    analytics: <AnalyticsDashboard data={data} />,
    recommendations: <RecommendationsDashboard data={data} />,
    drift: <DriftDashboard data={data} />,
    correlation: <CorrelationDashboard data={data} />,
    report: <ReportDashboard data={data} />,
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeDashboard}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
      >
        {views[activeDashboard]}
      </motion.div>
    </AnimatePresence>
  )
}
