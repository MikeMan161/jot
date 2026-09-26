import { Outlet } from "react-router"
import { SidebarProvider, SidebarInset, SidebarTrigger } from './ui/sidebar'
import AppSidebar from "./AppSidebar"
import DemoBanner from "./DemoBanner"

type AppLayoutProps = {
    token: string | null
}

export default function AppLayout({ token }: AppLayoutProps) {
    return (
        <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
                {/* Above the trigger so it reads as a property of the whole session
                    rather than of whichever page happens to be open. */}
                <DemoBanner token={token} />
                <SidebarTrigger />
                <Outlet />
            </SidebarInset>
        </SidebarProvider>
    )
}
