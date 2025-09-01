import json
import os
import uuid
import base64
from pathlib import Path
from config import WorkflowBuilder

class SmartRouterConfigBuilder:
    """智能路由器配置构建器，直接使用topoData_99_y.json中的路由配置"""
    
    def __init__(self):
        self.subnet_data = None
        self.topo_data = None
        self.routers = []
        self.route_configs = []
        self.builder = WorkflowBuilder()
        
    def load_subnet_data(self, subnet_file):
        """加载子网ip1拓扑文件"""
        with open(subnet_file, 'r', encoding='utf-8') as f:
            self.subnet_data = json.load(f)
        self.routers = self._extract_routers(self.subnet_data)
        print(f"✅ 从子网文件加载了 {len(self.routers)} 个路由器")
        return self.routers
    
    def load_topo_data(self, topo_file):
        """加载99拓扑数据用于匹配"""
        with open(topo_file, 'r', encoding='utf-8') as f:
            self.topo_data = json.load(f)
        
        # 提取路由配置
        self.route_configs = self.topo_data.get('route_config', [])
        print(f"✅ 加载拓扑数据: {len(self.route_configs)} 个路由器配置脚本")
        
        # 显示可用的路由IP配置
        route_ips = [cfg.get('ip', '') for cfg in self.route_configs]
        print(f"📝 可用路由配置IP: {', '.join(route_ips[:10])}{'...' if len(route_ips) > 10 else ''}")
        
    def match_and_configure(self):
        """智能匹配：直接使用topo数据中的节点信息进行匹配"""
        if not self.routers:
            raise ValueError("未加载路由器数据，请先调用load_subnet_data")
        if not self.topo_data:
            raise ValueError("未加载拓扑数据，请先调用load_topo_data")
            
        # 创建虚拟VMs用于workflow系统
        virtual_vms = []
        matched_configs = []  # 临时存储匹配的配置
        matched_count = 0
        
        # 获取topo数据中的节点信息
        topo_nodes = self.topo_data.get('nodes', [])
        route_config_dict = {cfg['ip']: cfg['script'] for cfg in self.route_configs}
        
        for router in self.routers:
            # 通过名称匹配topo节点
            router_name = router['name'].replace('Router_', '')  # 去掉Router_前缀
            
            matched_node = None
            for node in topo_nodes:
                if node.get('name') == router_name:
                    matched_node = node
                    break
            
            if matched_node:
                # 获取节点的所有IP地址
                node_ips = matched_node.get('ip', '').split(', ')
                
                # 查找对应的路由配置
                found_config = None
                config_ip = None
                for ip in node_ips:
                    if ip in route_config_dict:
                        found_config = route_config_dict[ip]
                        config_ip = ip
                        break
                
                if found_config:
                    # 创建虚拟VM
                    virtual_vm = {
                        'id': router['id'],  # 使用原始路由器ID
                        'name': router['name'],
                        'ip': router['ip'],
                        'vmType': 'DRT',
                        'service_type': 'router'
                    }
                    virtual_vms.append(virtual_vm)
                    
                    # 存储配置待后续添加
                    matched_configs.append({
                        'router_id': router['id'],
                        'config': found_config
                    })
                    
                    matched_count += 1
                    print(f"✅ 匹配路由器: {router['name']} -> 配置IP: {config_ip}")
                    print(f"   📍 节点子网: {matched_node.get('subnet', 'N/A')}")
                    print(f"   🌍 位置: {matched_node.get('city', 'N/A')}, {matched_node.get('nation', 'N/A')}")
                else:
                    print(f"⚠️  {router['name']} 匹配到节点但无路由配置")
            else:
                print(f"❌ 未匹配节点: {router['name']}")
                
        # 先设置虚拟VMs到builder
        self.builder.vms = virtual_vms
        
        # 然后添加配置任务
        for config_item in matched_configs:
            self.builder.exectask(config_item['router_id'], config_item['config'])
        
        print(f"✅ 总共匹配了 {matched_count} 个路由器配置")
        return matched_count
    
    def build_workflow_json(self, output_path):
        """生成workflow JSON文件"""
        if not self.builder.tasks:
            raise ValueError("未添加任何任务，请先调用match_and_configure")
            
        # 生成JSON
        self.builder.build_json(output_path)
        return output_path
    
    def _extract_routers(self, subnet_data):
        """从子网数据中提取路由器信息"""
        routers = []
        try:
            position_topos = subnet_data["fileData"]["otherData"]["positionTopos"]
        except Exception as e:
            print("解析子网positionTopos失败:", e)
            return []
            
        for item in position_topos:
            # 查找type为VM且vmType为DRT的路由器设备
            if item.get("type") == "VM" and item.get("vmType") == "DRT":
                router_info = {
                    "id": item["id"],
                    "name": item.get("name", ""),
                    "ip": item.get("rangeName", ""),
                    "x": item.get("x", "0"),
                    "y": item.get("y", "0"),
                    "properties": item.get("otherAttributeIns", [])
                }
                routers.append(router_info)
                
        print(f"[调试] 提取的路由器设备:")
        for router in routers[:5]:  # 只显示前5个
            print(f"  ID: {router['id']} | 名称: {router['name']} | IP: {router['ip']}")
        if len(routers) > 5:
            print(f"  ... 还有 {len(routers)-5} 个路由器")
            
        return routers


def main():
    """主函数示例"""
    # 文件路径配置
    subnet_file = "s:/项目/2025/ip/上传/子网ip1_topo.json"
    topo_file = "s:/项目/2025/ip/上传/99/topoData_99_y.json"
    output_file = "s:/项目/2025/ip/上传/003/smart_router_workflow.json"
    
    try:
        # 创建智能路由器配置构建器
        print("🚀 初始化智能路由器配置构建器...")
        builder = SmartRouterConfigBuilder()
        
        # 加载数据
        print("🔄 加载子网路由器数据...")
        routers = builder.load_subnet_data(subnet_file)
        
        print("🔄 加载拓扑匹配数据...")
        builder.load_topo_data(topo_file)
        
        # 匹配并配置
        print("🔄 智能匹配路由器并添加配置任务...")
        matched_count = builder.match_and_configure()
        
        if matched_count > 0:
            # 生成workflow JSON
            print("🔄 生成workflow JSON文件...")
            output_path = builder.build_workflow_json(output_file)
            print(f"✅ 成功生成智能路由器配置workflow: {output_path}")
            print(f"📊 匹配的路由器数量: {matched_count}")
            print(f"📋 生成的任务数量: {len(builder.builder.tasks)}")
        else:
            print("❌ 未匹配到任何路由器，无法生成workflow")
            
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
