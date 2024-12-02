import * as React from "react";
import {
  FileText, 
  PieChart,
  Layers,
  Command,
  Settings2,
  Send,
  LifeBuoy,
} from "lucide-react";
import { NavMain } from '@/components/shared/layout/NavMain';
import { NavSecondary } from '@/components/shared/layout/NavSecondary';
import { NavUser } from '@/components/shared/layout/NavUser';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const data = {
  user: {
    name: "Demo User",
    email: "demo@example.com",
    avatar: "/avatars/default.jpg",
  },
  navMain: [
    {
      title: "文本分析",
      url: "/text-analysis",
      icon: FileText,
      isActive: true,
      items: [
        {
          title: "文本评估",
          url: "/text-analysis/review",
        },
        {
          title: "文本分类",
          url: "/text-analysis/classification",
        },
      ],
    },
    {
      title: "数据可视化",
      url: "/visualization/reports",
      icon: PieChart,
      items: [
        {
          title: "分析报告",
          url: "/visualization/reports",
        },
      ],
    },
    {
      title: "数据管理",
      url: "/data/datasets",
      icon: Layers,
      items: [
        {
          title: "数据集",
          url: "/data/datasets",
        },
      ],
    },
    {
      title: "系统设置",
      url: "/settings",
      icon: Settings2,
      items: [
        {
          title: "通用设置",
          url: "/settings/general",
        },
        {
          title: "个人信息",
          url: "/settings/profile",
        },
      ],
    },
  ],
  navSecondary: [
    {
      title: "帮助中心",
      url: "/help",
      icon: LifeBuoy,
    },
    {
      title: "反馈建议",
      url: "/feedback",
      icon: Send,
    },
  ],
};

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar variant="inset" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="/">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <Command className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">分析平台</span>
                  <span className="truncate text-xs">AI 驱动的文本分析平台</span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        <NavSecondary items={data.navSecondary} className="mt-auto" />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
    </Sidebar>
  );
}