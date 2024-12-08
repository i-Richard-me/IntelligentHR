// src/components/features/feature-config/ConfigSidebar.tsx

import * as React from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { CheckCircle2, FileText, Database, Brain } from "lucide-react";

// 功能模块配置数据
export const featureModules = {
  data_cleaning: {
    id: 'data_cleaning',
    title: "数据清洗",
    description: "配置数据清洗功能的模型和向量数据库",
    icon: Database,
  },
  text_review: {
    id: 'text_review',
    title: "文本评估",
    description: "配置文本评估功能的参数和规则",
    icon: FileText,
  },
  text_classification: {
    id: 'text_classification',
    title: "文本分类",
    description: "配置文本分类的模型和类别",
    icon: CheckCircle2,
  },
  semantic_analysis: {
    id: 'semantic_analysis',
    title: "语义分析",
    description: "配置语义分析的模型和规则",
    icon: Brain,
  },
} as const;

export type FeatureModuleId = keyof typeof featureModules;

interface ConfigSidebarProps extends React.ComponentProps<typeof Sidebar> {
  activeModule: FeatureModuleId;
  onModuleChange: (moduleId: FeatureModuleId) => void;
}

export function ConfigSidebar({
  activeModule,
  onModuleChange,
  ...props
}: ConfigSidebarProps) {
  return (
    <Sidebar
      collapsible="none"
      className="hidden lg:flex h-full bg-background border-l"
      {...props}
    >
      <SidebarContent className="h-full">
        <SidebarGroup>
          <SidebarGroupLabel>功能模块</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {Object.entries(featureModules).map(([id, module]) => (
                <SidebarMenuItem key={id}>
                  <SidebarMenuButton
                    onClick={() => onModuleChange(id as FeatureModuleId)}
                    isActive={activeModule === id}
                  >
                    <module.icon className="h-4 w-4" />
                    <span>{module.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  );
}