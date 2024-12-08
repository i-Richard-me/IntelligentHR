import * as React from "react";
import {
  FileText, 
  PieChart,
  Layers,
  Command,
  Settings2,
  Send,
  LifeBuoy,
  Database
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
  SidebarRail,
} from "@/components/ui/sidebar";

const data = {
  user: {
    name: "Demo User",
    email: "demo@example.com",
    avatar: "",
  },
  navMain: [
    {
      title: "文本分析",
      url: "#",
      icon: FileText,
      isActive: true,
      items: [
        {
          title: "文本评估",
          url: "/text-review",
        },
        {
          title: "文本分类",
          url: "/text-classification",
        },
      ],
    },
    {
      title: "数据处理",
      url: "#",
      icon: Database,
      isActive: true,
      items: [
        {
          title: "数据清洗",
          url: "/data-cleaning",
        },
      ],
    },
    {
      title: "数据可视化",
      url: "#",
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
      url: "",
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
      url: "",
      icon: Settings2,
      isActive: true,
      items: [
        {
          title: "功能配置",
          url: "/feature-config",
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
    <Sidebar className="border-r-0" {...props}>
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
        <NavMain items={data.navMain} />
      </SidebarHeader>
      <SidebarContent>
        <NavSecondary items={data.navSecondary} className="mt-auto" />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}