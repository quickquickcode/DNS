#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能路由器配置命令解码器
用于查看生成的workflow中真实的VyOS路由配置脚本
"""

import json
import base64

def decode_smart_router_commands(workflow_file):
    """解码智能workflow文件中的真实VyOS配置脚本"""
    print("=" * 60)
    print("智能路由器配置命令解码器 v2.0")
    print("展示真实的VyOS路由配置脚本")
    print("=" * 60)
    
    try:
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        trac_list = workflow_data['templateData']['tracList']
        
        print(f"📋 工作流包含 {len(trac_list)} 个真实路由配置任务")
        print()
        
        # 按设备分组显示配置脚本
        device_configs = {}
        
        for i, trac in enumerate(trac_list, 1):
            device_name = trac['deviceName']
            cmd = trac['metadata']['cmd']
            
            # 提取base64部分并解码
            if ' | base64 -d | bash' in cmd:
                base64_part = cmd.split(' | base64 -d | bash')[0].replace('echo ', '')
                try:
                    decoded_script = base64.b64decode(base64_part).decode('utf-8')
                    
                    print(f"🖥️  设备 #{i}: {device_name}")
                    print(f"📝 VyOS路由配置脚本:")
                    print("```bash")
                    print(decoded_script)
                    print("```")
                    print("-" * 60)
                    
                    # 分析配置内容
                    if 'set protocols ospf' in decoded_script:
                        ospf_networks = decoded_script.count('set protocols ospf area 0 network')
                        print(f"   🔄 OSPF配置: {ospf_networks} 个网络")
                    
                    if 'set protocols bgp' in decoded_script:
                        bgp_neighbors = decoded_script.count('neighbor')
                        print(f"   🌐 BGP配置: {bgp_neighbors} 个邻居")
                    
                    if 'redistribute' in decoded_script:
                        print(f"   ↗️  路由重分发: 已配置")
                    
                    print()
                        
                except Exception as e:
                    print(f"❌ 解码失败 ({device_name}): {str(e)}")
        
        print(f"\n✅ 解码完成! 共处理 {len(trac_list)} 个真实VyOS路由器配置")
        print(f"💡 所有配置均来自topoData_99_y.json的route_config部分")
        
    except Exception as e:
        print(f"❌ 解码失败: {str(e)}")

def main():
    """主函数"""
    workflow_file = "s:/项目/2025/ip/上传/003/smart_router_workflow.json"
    decode_smart_router_commands(workflow_file)

if __name__ == "__main__":
    main()
