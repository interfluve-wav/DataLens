import { DataLensProvider, useDataLens } from "@/context/DataLensContext"
import { UploadHero } from "@/components/layout/UploadHero"
import { AppShell } from "@/components/layout/AppShell"

function DataLensApp() {
  const { data } = useDataLens()
  return data ? <AppShell /> : <UploadHero />
}

export default function App() {
  return (
    <DataLensProvider>
      <DataLensApp />
    </DataLensProvider>
  )
}
