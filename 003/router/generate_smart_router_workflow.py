#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能路由器配置脚本生成器
直接使用topoData_99_y.json中的真实路由配置脚本
"""

from smart_router_config import SmartRouterConfigBuilder

def main():
    """主执行函数"""
    print("=" * 60)
    print("智能路由器配置脚本生成器 v2.0")
    print("使用真实topoData路由配置脚本")
    print("=" * 60)
    
    # 配置文件路径
    SUBNET_FILE = "s:/项目/2025/ip/上传/子网ip1_topo.json"
    TOPO_FILE = "s:/项目/2025/ip/上传/99/topoData_99_y.json"
    OUTPUT_FILE = "s:/项目/2025/ip/上传/003/smart_router_workflow.json"
    
    try:
        # 创建智能路由器配置构建器
        print("🚀 初始化智能路由器配置构建器...")
        builder = SmartRouterConfigBuilder()
        
        # 步骤1: 加载子网路由器数据
        print("\n📂 步骤1: 加载子网路由器数据...")
        routers = builder.load_subnet_data(SUBNET_FILE)
        if not routers:
            print("❌ 未在子网数据中找到路由器设备")
            return
        
        print(f"📊 发现 {len(routers)} 个路由器设备")
        
        # 步骤2: 加载拓扑配置数据
        print(f"\n📂 步骤2: 加载拓扑配置数据...")
        builder.load_topo_data(TOPO_FILE)
        
        # 步骤3: 智能匹配路由器并添加真实配置任务
        print(f"\n🔄 步骤3: 智能匹配路由器并生成真实配置任务...")
        matched_count = builder.match_and_configure()
        
        if matched_count == 0:
            print("❌ 未能匹配任何路由器配置")
            print("💡 建议检查路由器名称和topo节点名称的匹配关系")
            return
        
        # 步骤4: 生成workflow JSON文件
        print(f"\n📝 步骤4: 生成workflow JSON文件...")
        output_path = builder.build_workflow_json(OUTPUT_FILE)
        
        # 输出统计信息
        print(f"\n✅ 执行完成!")
        print(f"📄 输出文件: {output_path}")
        print(f"🎯 匹配路由器数量: {matched_count}/{len(routers)}")
        print(f"📋 生成任务数量: {len(builder.builder.tasks)}")
        
        # 显示配置类型统计
        if builder.builder.tasks:
            print(f"\n📋 配置脚本统计:")
            print(f"  - 真实VyOS路由配置: {len(builder.builder.tasks)} 个")
            print(f"  - 包含OSPF/BGP协议配置")
            print(f"  - 自动化网络拓扑配置")
        
        print(f"\n🎉 智能路由器配置workflow已成功生成!")
        print(f"💡 所有配置脚本均来自真实的topoData_99_y.json!")
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        print("💡 请检查文件路径是否正确")
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {str(e)}")
        import traceback
        print("\n🔍 详细错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
