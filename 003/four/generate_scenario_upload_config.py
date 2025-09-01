from config import WorkflowBuilder

# ======================== 配置参数 ========================
# 拓扑数据文件路径 - 包含网络节点和服务信息的JSON文件
TOPO_PATH = "./01源文件/1000/topoData_1000_上传.json"


# 目标服务类型 - 指定要处理的DNS服务类型
# 
SERVICE_KEY = "gzdx_dns_client_0.7"

# 输出工作流文件路径 - 生成的workflow JSON文件保存位置
OUTPUT_JSON = "./01源文件/1000/workflow_致盲_1000.json"

# 目标路径模板 - VM中文件的目标存放路径（已弃用，使用动态路径）
TARGET_PATH = '/home/client/'+'dig.go'

# 源文件基础目录 - 本地存储四场景脚本的根目录
BASE_UPLOAD_DIR = "./01源文件/1000/1000四场景脚本/四场景脚本"

# 场景路径映射
# 这个地方可以使用一个或多个字典来映射不同场景的路径
SCENARIO_PATHS = {
    "致盲风险": "致盲风险/blind (1)/blind (1)/dns_Blind",
    # "孤立风险": "孤立风险/isolate/isolate (1)/dns_Isolate"
}

TARGET_IP = "202.118.0.16"

# ======================== 主程序 ========================
# gzdx_dns_client_chain_0.2 无需导入是正常现象
times = 0

if __name__ == "__main__":
    import os
    builder = WorkflowBuilder()
    vms = builder.loadfile(TOPO_PATH, SERVICE_KEY)
    print(f"共发现{len(vms)}台目标VM")
    for vm in vms:
        # print(f"🎯 处理VM: {vm['name']} ({vm['ip']})")
        if vm["ip"] != TARGET_IP:
            # print(f"⚠️  跳过非目标IP: {vm['ip']}")
            continue
        vm_file_count = 0
        print(f"🎯 处理VM: {vm['name']} ({vm['ip']})")
        
        # 处理每个场景
        for scenario_name, scenario_relative_path in SCENARIO_PATHS.items():
            print(f"📂 处理场景: {scenario_name}")
            print(f"   本地路径: {BASE_UPLOAD_DIR}\\{scenario_relative_path}")
            print(f"   目标VM: {vm['name']} ({vm['ip']})")
            
            # 构建完整路径
            scenario_full_path = os.path.join(BASE_UPLOAD_DIR, scenario_relative_path)
            
            if not os.path.exists(scenario_full_path):
                print(f"⚠️  路径不存在: {scenario_full_path}")
                print(f"  ⚠️  {scenario_name}: 路径不存在或无文件")
                continue
            
            # 遍历场景目录中的所有文件
            files = os.listdir(scenario_full_path)
            scenario_file_count = 0
            
            for fname in files:
                fpath = os.path.join(scenario_full_path, fname)
                if os.path.isfile(fpath):
                    # 构造远程目标路径
                    target_path = f"/opt/scenarios/{scenario_name}/{fname}"
                    
                    # 每个文件单独创建一个导入任务
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 文件: {fname} -> {target_path}")
                    scenario_file_count += 1
                    times += 1
            
#             if scenario_file_count > 0:
#                 print(f"  📊 {scenario_name}: 添加了 {scenario_file_count} 个文件上传任务")
#                 vm_file_count += scenario_file_count
                
#                 # 添加场景部署脚本执行任务
#                 deploy_command = f"""
# echo "🚀 部署 {scenario_name} 场景脚本..."
# mkdir -p /opt/scenarios/{scenario_name}
# cd /opt/scenarios/{scenario_name}
# chmod +x *.sh 2>/dev/null || true
# echo "✅ {scenario_name} 场景部署完成"
# ls -la /opt/scenarios/{scenario_name}/
# """
#                 builder.exectask(device_id=vm["id"], command_str=deploy_command.strip())
#                 print(f"  🚀 执行部署脚本: {scenario_name}")
        
        print(f"  ✅ VM完成: 上传 {vm_file_count} 个文件")
    # 示例：添加命令执行任务
    # 添加一个执行命令任务示例（对第一个VM）
    # if vms:
    #     builder.exectask(device_id=vms[0]["id"], command_str="echo hello > /tmp/hello.txt")
    builder.build_json(OUTPUT_JSON)
    print(f"已生成workflow: {OUTPUT_JSON}")
    print(f"总共添加了 {times} 个文件导入任务")

