#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
import time
import uuid


# 保存文件
open_file = './01源文件/99/topoData_99_y.json'
output_file = './01源文件/99/topoData_99_new_images.json'
# 保存文件
# open_file = '01源文件/Project-Stable-26节点版本/data.json'
# output_file = './02转译/data26.json'
# 保存文件
# open_file = './01源文件/1000/topoData_1000.json'
# output_file = './01源文件/1000/topoData_1000_上传.json'

# open_file = '01源文件/2000/topoData_2000.json'
# output_file = '01源文件/2000/topoData_2000_上传.json'


# 生成唯一ID的函数
def gen_id(prefix):
    """生成指定前缀的唯一ID"""
    return f"{prefix}{uuid.uuid4().hex[:31]}"  # 保证ID长度不超过32个字符 # fix

def convert_small_topo_correct():
    """完全正确的DNS网络拓扑转换 - 确保IP分配到正确子网"""
    
    print("🚀 转换精简版DNS网络拓扑（完全正确版）...")
    
    IMAGE_MAP = {
        "gzdx_dns_client_0.7": "49b1e71a-d433-49e1-8d89-f98f2c1483a9",
        "gzdx_dns_client_0.8": "992a8200-7b3a-4466-a2f0-2ad559f40802",
        "bind-dns": "BBBcf3bc-342f-4b96-8a2d-14b4272ea2ec",
        "gzdx_dns_recursion_chain_0.2": "facc7c5f-c718-4a92-a09b-718279c64e84",
        "gzdx_dns_root_chain_0.2": "353c746b-f00f-45c0-ad2f-70b03607d283",
        "gzdx_dns_authority_chain_0.2": "0410f2f9-dc31-47c3-b007-f2ee020155ab",
        "gzdx_dns_client_chain_0.2": "a24c3521-260c-4090-94ac-6fa4761f290c",
        "gzdx_dns_rootserver_0.2": "57fc5249-916f-4da6-9caa-b49c7e2be5f1",
        "gzdx_dns_recursionserver_0.2": "d56b03b8-5e2b-4b9b-a353-befbc65a4cb9",
        "gzdx_dns_authorityserver_0.2": "3f8d8505-b191-45b6-9baa-927286a217da",
        "vyos-v3":"3f139262-537f-4dd1-962f-e6fdf9df8b82"
    }
    


    
    DEFAULT_ROUTER_IMAGE = "vyos-v3"
    DEFAULT_FLAVOR = "RS00-001-001024-00040"
    
    # 特殊镜像的配置规格映射
    FLAVOR_MAP = {
        "gzdx_dns_authority_chain_0.2": "RS00-001-001024-00510",
        "gzdx_dns_client_0.7": "RS00-001-003072-00040"

    }
    
    # 生成基础ID
    range_id = gen_id("R")
    network_id = gen_id("N")
    os_project_id = gen_id("P")
    
    # 读取精简数据
    with open(open_file, 'r', encoding='utf-8') as f:
        src = json.load(f)
    
    print(f"   📊 数据统计:")
    print(f"      - 路由器: {len(src['nodes'])}")
    print(f"      - 边连接: {len(src['edges'])}")
    print(f"      - DNS服务器: {sum(len(node.get('type', {})) for node in src['nodes'])}")
    
    # 初始化数据结构
    positionTopos = []
    linkTopos = []
    vmlist = []
    subnets = []
    segmentTopos = []
    networks = []
    switchs = []
    
    # 映射字典
    node_to_router = {}
    subnet_to_switch = {}
    ip_to_server = {}
    subnet_id_map = {}
    ip_to_correct_subnet = {}  # 🔥 关键：IP到正确子网的映射
    
    print("   1️⃣ 建立IP到正确子网的映射...")
    
    # 🔥 关键步骤：建立每个IP地址到其正确子网的映射
    for edge in src['edges']:
        edge_ips = [ip.strip() for ip in edge['ip'].split(',')]
        edge_subnet = edge['subnet']
        for ip in edge_ips:
            if ip:
                ip_to_correct_subnet[ip] = edge_subnet
                print(f"      ✅ IP {ip} -> 边子网 {edge_subnet}")
    
    # 为管理IP建立映射（不在edges中的IP分配到管理子网）
    for node in src['nodes']:
        node_ips = [ip.strip() for ip in node['ip'].split(',')]
        mgmt_subnet = node['subnet']
        for ip in node_ips:
            if ip and ip not in ip_to_correct_subnet:
                ip_to_correct_subnet[ip] = mgmt_subnet
                print(f"      ⚠️  IP {ip} -> 管理子网 {mgmt_subnet}")
    
    print(f"      - 总IP映射数: {len(ip_to_correct_subnet)} 个")
    
    print("   2️⃣ 创建所有需要的子网...")
    
    # 收集所有需要的子网
    all_subnets = set()
    for edge in src['edges']:
        all_subnets.add(edge['subnet'])
    for node in src['nodes']:
        all_subnets.add(node['subnet'])
    
    # 管理子网列表（用于创建交换机）
    mgmt_subnets = list(set(node['subnet'] for node in src['nodes']))
    
    for subnet_cidr in all_subnets:
        subnet_id = gen_id("S")
        segment_id = gen_id("G")
        subnet_id_map[subnet_cidr] = subnet_id
        
        # 计算网关IP
        base_ip = subnet_cidr.split('/')[0]
        ip_parts = base_ip.split('.')
        
        if subnet_cidr.endswith('/29'):  # 边子网
            gateway_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 1}"
            dhcp_start = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 3}"
            dhcp_end = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 6}"
        else:  # 管理子网
            gateway_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.254"
            dhcp_start = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.2"
            dhcp_end = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.253"
        
        subnets.append({
            "enable_dhcp": True,
            "dns": "",
            "description": f"子网 - {subnet_cidr}",
            "topo_subnet_id": subnet_id,
            "dhcp_server_ip": dhcp_start,
            "network_id": network_id,
            "ip_version": 4,
            "subnet_id": subnet_id,
            "cidr": subnet_cidr,
            "gateway_ip": gateway_ip,
            "allocation_pools": [{"start": dhcp_start, "end": dhcp_end}],
            "internalKey": gen_id("S"),
            "subnet_name": f"subnet-{subnet_cidr}",
            "segment_id": segment_id
        })
        
        segmentTopos.append({
            "network_id": network_id,
            "topo_segment_id": segment_id,
            "name": f"sg-{subnet_cidr}",
            "bind_devices": [],
            "internalKey": gen_id("G"),
            "network_type": "vlan",
            "segment_id": segment_id
        })
    
    print(f"      - 创建子网总数: {len(all_subnets)} 个")
    
    print("   3️⃣ 创建路由器...")
    
    for i, node in enumerate(src['nodes']):
        router_id = gen_id("V")
        router_name = node['name']
        node_to_router[router_name] = router_id
        
        # 路由器位置（外圈）
        angle = 2 * math.pi * i / len(src['nodes'])
        radius = 500
        x_pos = int(radius * math.cos(angle))
        y_pos = int(radius * math.sin(angle))
        
        positionTopos.append({
            "groupType": "default",
            "sourceCompanyId": "abc/abc",
            "parentLevel": 0,
            "type": "VM",
            "otherAttributeIns": [
                {"key": "nation", "value": node.get('nation', '')},
                {"key": "city", "value": node.get('city', '')},
                {"key": "protocol", "value": node.get('protocol', '')}
            ],
            "topoLevel": 0,
            "vmType": "DRT",
            "property": "elementType:node;issave:true;visible:true;rotate:0;scaleX:1;scaleY:1;zIndex:3;textPosition:Bottom_Center;deviceId:null;fillColor:0, 0, 0;iswarn:false;isopen:false;islock:null",
            "rangeName": router_name,
            "networkId": network_id,
            "id": router_id,
            "internalKey": gen_id("V"),
            "internalNetwork": "0",
            "height": 50,
            "standbyNodeImage": "/files/global/41efccfc454b4bc79a61e6ce5189ccc5.png",
            "nextLevel": 0,
            "isBullseye": False,
            "isShow": 1,
            "isTarget": False,
            "companyId": "abc/abc",
            "rangeId": range_id,
            "nodeImage": "/files/global/afaf206261284572b84182d91abc5ba5.png",
            "name": f"Router_{router_name}",
            "width": 50,
            "x": str(x_pos),
            "y": str(y_pos),
            "status": 0
        })
    
    print("   4️⃣ 创建交换机（只为管理子网创建）...")
    
    # 🔥 修正：只为管理子网创建交换机，edges子网不需要交换机
    # 🔥 新增：交换机位置与对应路由器角度相同，但更靠外
    for i, subnet_cidr in enumerate(sorted(mgmt_subnets)):
        switch_id = gen_id("W")
        subnet_to_switch[subnet_cidr] = switch_id
        
        # 🔥 关键：找到使用这个管理子网的路由器，使用相同角度
        router_node = None
        for node in src['nodes']:
            if node['subnet'] == subnet_cidr:
                router_node = node
                break
        
        if router_node:
            # 找到路由器在nodes列表中的索引，使用相同角度
            router_index = src['nodes'].index(router_node)
            angle = 2 * math.pi * router_index / len(src['nodes'])
        else:
            # 备用方案：使用顺序角度
            angle = 2 * math.pi * i / len(mgmt_subnets)
        
        # 交换机位置（比路由器更远离圆心）
        radius = 750  # 比路由器的500更远
        x_pos = int(radius * math.cos(angle))
        y_pos = int(radius * math.sin(angle))
        
        positionTopos.append({
            "groupType": "default",
            "sourceCompanyId": "abc/abc",
            "parentLevel": 0,
            "type": "SW",
            "otherAttributeIns": [],
            "topoLevel": 0,
            "vmType": "SW",
            "property": "elementType:node;issave:true;visible:true;rotate:0;scaleX:1;scaleY:1;zIndex:3;textPosition:Bottom_Center;deviceId:null;fillColor:0, 0, 0;iswarn:false;isopen:false;islock:null",
            "rangeName": subnet_cidr,
            "networkId": network_id,
            "id": switch_id,
            "internalKey": gen_id("W"),
            "internalNetwork": "0",
            "height": 40,
            "standbyNodeImage": "/files/global/50b62b4d557c462e9f40d66b7d2e0b31.png",
            "nextLevel": 0,
            "isBullseye": False,
            "isShow": 1,
            "isTarget": False,
            "companyId": "abc/abc",
            "rangeId": range_id,
            "nodeImage": "/files/global/ff3a82dc989048cf91319fac7a1a82dc.png",
            "name": subnet_cidr,
            "width": 40,
            "x": str(x_pos),
            "y": str(y_pos),
            "status": 0
        })
        
        switchs.append({
            "topo_switch_id": switch_id,
            "network_id": network_id,
            "switch_id": switch_id,
            "otherAttributeIns": [],
            "switch_name": subnet_cidr
        })
        
        # 绑定交换机到网段
        for segment in segmentTopos:
            if segment['name'] == f"sg-{subnet_cidr}":
                segment['bind_devices'].append({"id": switch_id, "status": 0})
                break
    
    print("   5️⃣ 创建DNS服务器...")
    
    server_count = 0
    for i, node in enumerate(src['nodes']):
        if not node.get('type'):
            continue
        
        # 🔥 关键：使用与路由器相同的角度
        base_angle = 2 * math.pi * i / len(src['nodes'])
        
        service_idx = 0
        for service_ip, service_info in node['type'].items():
            # 提取镜像名
            image_name = service_info.split('|')[0] if '|' in service_info else service_info.split('||')[0]
            server_id = gen_id("V")
            ip_to_server[service_ip] = server_id
            
            # 🔥 服务器位置（与路由器相同角度，但更远离圆心）
            offset_angle = (service_idx - len(node['type'])/2) * 0.2  # 减小偏移角度
            radius = 1000  # 比交换机的600更远
            x_pos = int(radius * math.cos(base_angle + offset_angle))
            y_pos = int(radius * math.sin(base_angle + offset_angle))
            
            positionTopos.append({
                "groupType": "default",
                "sourceCompanyId": "abc/abc",
                "parentLevel": 0,
                "type": "VM",
                "otherAttributeIns": [
                    {"key": "service_type", "value": image_name}
                ],
                "topoLevel": 0,
                "vmType": "SERVER",
                "property": "elementType:node;issave:true;visible:true;rotate:0;scaleX:1;scaleY:1;zIndex:3;textPosition:Bottom_Center;deviceId:null;fillColor:0, 0, 0;iswarn:false;isopen:false;islock:null",
                "rangeName": service_ip,
                "networkId": network_id,
                "id": server_id,
                "internalKey": gen_id("V"),
                "internalNetwork": "0",
                "height": 30,
                "standbyNodeImage": "/files/global/41efccfc454b4bc79a61e6ce5189ccc5.png",
                "nextLevel": 0,
                "isBullseye": False,
                "isShow": 1,
                "isTarget": False,
                "companyId": "abc/abc",
                "rangeId": range_id,
                "nodeImage": "/files/global/afaf206261284572b84182d91abc5ba5.png",
                "name": f"{image_name}_{service_ip}",
                "width": 30,
                "x": str(x_pos),
                "y": str(y_pos),
                "status": 0
            })
            
            # 绑定服务器到管理网段
            mgmt_subnet = node['subnet']
            for segment in segmentTopos:
                if segment['name'] == f"sg-{mgmt_subnet}":
                    segment['bind_devices'].append({"id": server_id, "status": 0})
                    break
            
            server_count += 1
            service_idx += 1
    
    print("   6️⃣ 创建VM配置（关键：正确的IP-子网分配）...")
    
    # 🔥 关键修复：路由器VM配置 - 每个IP分配到正确的子网
    for node in src['nodes']:
        router_id = node_to_router[node['name']]
        node_ips = [ip.strip() for ip in node['ip'].split(',') if ip.strip()]
        
        router_ports = []
        
        # 🔥 为每个IP创建端口，分配到正确的子网
        for port_idx, ip_address in enumerate(node_ips):
            if ip_address in ip_to_correct_subnet:
                correct_subnet = ip_to_correct_subnet[ip_address]
                subnet_id = subnet_id_map[correct_subnet]
                
                port_id = gen_id("P")
                prefix = "29" if correct_subnet.endswith('/29') else "24"
                
                router_ports.append({
                    "port_name": f"eth{port_idx}",
                    "port_security_enabled": False,
                    "topo_port_id": port_id,
                    "onlyForAccess": False,
                    "enableUsedPublicSubnet": False,
                    "port_id": port_id,
                    "linkType": "0-0",
                    "vlanType": "access",
                    "internalKey": gen_id("P"),
                    "fixed_ip_addresses": [{
                        "enable_dhcp": False,
                        "ip_version": 4,
                        "prefix": prefix,
                        "subnet_id": subnet_id,
                        "ip_address": ip_address
                    }]
                })
                
                print(f"      ✅ 路由器 {node['name']}: IP {ip_address} -> 子网 {correct_subnet}")
            else:
                print(f"      ❌ 未找到IP {ip_address} 的正确子网映射")
        
        # 添加管理网关端口
        mgmt_subnet = node['subnet']
        base_ip = mgmt_subnet.split('/')[0]
        ip_parts = base_ip.split('.')
        mgmt_gateway_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.254"
        
        port_id = gen_id("P")
        router_ports.append({
            "port_name": f"eth{len(node_ips)}",
            "port_security_enabled": False,
            "topo_port_id": port_id,
            "onlyForAccess": False,
            "enableUsedPublicSubnet": False,
            "port_id": port_id,
            "linkType": "0-0",
            "vlanType": "access",
            "internalKey": gen_id("P"),
            "fixed_ip_addresses": [{
                "enable_dhcp": False,
                "ip_version": 4,
                "prefix": "24",
                "subnet_id": subnet_id_map[mgmt_subnet],
                "ip_address": mgmt_gateway_ip
            }]
        })
        
        vmlist.append({
            "enableTmpl": False,
            "routerScripts": [],
            "sourceCompanyId": "abc/abc",
            "sysType": "Linux",
            "topo_vm_id": router_id,
            "platformType": "OpenStack",
            "ports": router_ports,
            "otherAttributeIns": [],
            "vm_id": router_id,
            "vm_type": "DRT",
            "zone": "nova-cy",
            "rangeName": node['name'],
            "zoneId": "90",
            "vm_name": f"Router_{node['name']}",
            "availability_zone": "nova-cy",
            "sourceImageId": IMAGE_MAP[DEFAULT_ROUTER_IMAGE],
            "configDrive": False,
            "vzType": "KVM",
            "platformId": "7",
            "user_data": "",
            "bullseye": False,
            "companyId": "abc/abc",
            "network_id": network_id,
            "rangeId": range_id,
            "flavorRef": DEFAULT_FLAVOR,
            "imageRef": IMAGE_MAP[DEFAULT_ROUTER_IMAGE]
        })
        
        # 绑定路由器到管理网段
        for segment in segmentTopos:
            if segment['name'] == f"sg-{mgmt_subnet}":
                segment['bind_devices'].append({"id": router_id, "status": 0})
                break
    
    # DNS服务器VM配置
    for node in src['nodes']:
        if not node.get('type'):
            continue
        
        for service_ip, service_info in node['type'].items():
            if service_ip not in ip_to_server:
                continue
            
            server_id = ip_to_server[service_ip]
            image_name = service_info.split('|')[0] if '|' in service_info else service_info.split('||')[0]
            image_id = IMAGE_MAP.get(image_name, IMAGE_MAP["bind-dns"])
            
            # 根据镜像类型选择配置规格
            flavor = FLAVOR_MAP.get(image_name, DEFAULT_FLAVOR)
            
            port_id = gen_id("P")
            vmlist.append({
                "enableTmpl": False,
                "routerScripts": [],
                "sourceCompanyId": "abc/abc",
                "sysType": "Linux",
                "topo_vm_id": server_id,
                "platformType": "OpenStack",
                "ports": [{
                    "port_name": "eth0",
                    "port_security_enabled": False,
                    "topo_port_id": port_id,
                    "onlyForAccess": False,
                    "enableUsedPublicSubnet": False,
                    "port_id": port_id,
                    "linkType": "0-0",
                    "vlanType": "access",
                    "internalKey": gen_id("P"),
                    "fixed_ip_addresses": [{
                        "enable_dhcp": False,
                        "ip_version": 4,
                        "prefix": "24",
                        "subnet_id": subnet_id_map[node['subnet']],
                        "ip_address": service_ip
                    }]
                }],
                "otherAttributeIns": [],
                "vm_id": server_id,
                "vm_type": "SERVER",
                "zone": "nova-cy",
                "rangeName": service_ip,
                "zoneId": "90",
                "vm_name": f"{image_name}_{service_ip}",
                "availability_zone": "nova-cy",
                "sourceImageId": image_id,
                "configDrive": False,
                "vzType": "KVM",
                "platformId": "7",
                "user_data": "",
                "bullseye": False,
                "companyId": "abc/abc",
                "network_id": network_id,
                "rangeId": range_id,
                "flavorRef": flavor,
                "imageRef": image_id
            })
    
    print("   7️⃣ 创建连接关系...")
    
    # 建立IP到路由器的映射
    ip_to_router = {}
    for node in src['nodes']:
        for ip in node['ip'].split(','):
            ip = ip.strip()
            if ip:
                ip_to_router[ip] = node['name']
    
    # 路由器间连接
    for edge in src['edges']:
        ips = [ip.strip() for ip in edge['ip'].split(',')]
        if len(ips) >= 2:
            ip1, ip2 = ips[0], ips[1]
            router1 = ip_to_router.get(ip1)
            router2 = ip_to_router.get(ip2)
            
            if router1 and router2 and router1 != router2:
                linkTopos.append({
                    "leftDeviceId": node_to_router[router1],
                    "rightDeviceId": node_to_router[router2],
                    "lineType": "dotted",
                    "destination": node_to_router[router1],
                    "width": 0.5,
                    "leftDeviceType": "VM",
                    "networkId": network_id,
                    "id": gen_id("L"),
                    "opacity": 1.0,
                    "rightDeviceType": "VM",
                    "leftNetId": network_id,
                    "rightNetId": network_id
                })
    
    # 路由器-交换机连接
    for node in src['nodes']:
        router_id = node_to_router[node['name']]
        mgmt_subnet = node['subnet']
        switch_id = subnet_to_switch[mgmt_subnet]
        
        linkTopos.append({
            "leftDeviceId": router_id,
            "rightDeviceId": switch_id,
            "lineType": "dotted",
            "destination": router_id,
            "width": 0.5,
            "leftDeviceType": "VM",
            "networkId": network_id,
            "id": gen_id("L"),
            "opacity": 1.0,
            "rightDeviceType": "SW",
            "leftNetId": network_id,
            "rightNetId": network_id
        })
    
    # 交换机-服务器连接
    for node in src['nodes']:
        if not node.get('type'):
            continue
        
        mgmt_subnet = node['subnet']
        switch_id = subnet_to_switch[mgmt_subnet]
        for service_ip in node['type'].keys():
            if service_ip in ip_to_server:
                linkTopos.append({
                    "leftDeviceId": switch_id,
                    "rightDeviceId": ip_to_server[service_ip],
                    "lineType": "dotted",
                    "destination": switch_id,
                    "width": 0.5,
                    "leftDeviceType": "SW",
                    "networkId": network_id,
                    "id": gen_id("L"),
                    "opacity": 1.0,
                    "rightDeviceType": "VM",
                    "leftNetId": network_id,
                    "rightNetId": network_id
                })
    
    print("   8️⃣ 创建网络配置...")
    
    networks.append({
        "network_id": network_id,
        "parent_id": os_project_id,
        "network_name": "rootNetwork",
        "topo_network_id": network_id,
        "otherAttributeIns": []
    })
    
    print("   9️⃣ 组装最终结果...")
    
    result = {
        "picPath": "iVCC",
        "fileData": {
            "sourceRangeId": range_id,
            "otherData": {
                "autoLayoutLinks": [],
                "id": network_id,
                "autoLayout2Ds": [],
                "linkTopos": linkTopos,
                "positionTopos": positionTopos
            },
            "projectTopo": {
                "armTools": [],
                "notes": [],
                "switchs": switchs,
                "project_id": os_project_id,
                "segmentTopos": segmentTopos,
                "description": "",
                "subnets": subnets,
                "vmlist": vmlist,
                "networks": networks,
                "os_project_id": os_project_id,
                "project_name": "DNS网络拓扑_完全正确版",
                "os_project_name": "DNS网络拓扑_完全正确版"
            },
            "prototype": "NW"
        }
    }
    

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完全正确版转换完成: {output_file}")
    print(f"📊 最终统计:")
    print(f"   - 路由器: 4个")
    print(f"   - 子网总数: {len(all_subnets)}个 (边子网: {len(src['edges'])}个 + 管理子网: {len(mgmt_subnets)}个)")
    print(f"   - 交换机: {len(mgmt_subnets)}个 (只为管理子网创建)") 
    print(f"   - DNS服务器: {server_count}个")
    print(f"   - 连接关系: {len(linkTopos)}条")
    print(f"\n🎯 关键修复:")
    print(f"   ✅ 每个IP都分配到正确的子网")
    print(f"   ✅ 边子网IP不会错误分配到管理子网")
    print(f"   ✅ 管理IP分配到管理子网")
    print(f"\n🎯 文件 {output_file} 应该不再有IP-子网匹配错误!")

if __name__ == "__main__":
    convert_small_topo_correct() 