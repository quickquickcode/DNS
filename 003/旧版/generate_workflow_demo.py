from config import WorkflowBuilder

# ======================== 配置参数 ========================
# 拓扑数据文件路径 - 包含网络节点和服务信息的JSON文件
TOPO_PATH = "./02转译/topoData_99_完全正确版.json"
TOPO_PATH = "./06/129-测试-sss_forma.json"
TOPO_PATH = "./06/导出模版_formatted_20250729_151612.json"
TOPO_PATH = "01源文件/1000/topoData_1000_上传.json"

# 目标服务类型 - 指定要处理的DNS服务类型
# 
SERVICE_KEY = "gzdx_dns_client_0.7"

# 输出工作流文件路径 - 生成的workflow JSON文件保存位置
OUTPUT_JSON = "./003/workflow_demo.json"
OUTPUT_JSON = "./06/workflow_demo.json"
OUTPUT_JSON = "01源文件/1000/workflow_demo_1000.json"

# 目标路径模板 - VM中文件的目标存放路径（已弃用，使用动态路径）
TARGET_PATH = '/home/client/'+'dig.go'

# 源文件基础目录 - 本地存储DNS配置文件的根目录
BASE_UPLOAD_DIR = "./01源文件/99/DNS_99_y/DNS_99_y"
BASE_UPLOAD_DIR = "./01源文件/1000/DNS_1000_y/DNS_1000_y"

# ======================== 主程序 ========================
# gzdx_dns_client_chain_0.2 无需导入是正常现象

if __name__ == "__main__":
    import os
    builder = WorkflowBuilder()
    vms = builder.loadfile(TOPO_PATH, SERVICE_KEY)
    print(f"共发现{len(vms)}台目标VM")
    for vm in vms:
        # print(f"处理VM: {vm['name']} ({vm['ip']})")
        # 解析name，提取类型和IP
        # 假设name格式: gzdx_dns_authorityserver_0.2_202.118.3.12(202.118.3.12)
        import re
        # 只提取类型和IP，忽略其它内容
        m = re.match(r"gzdx_dns_([a-zA-Z]+(?:_chain|server)?).*_(\d+\.\d+\.\d+\.\d+)", vm["name"])
        if not m:
            print(f"无法解析VM名称: {vm['name']}")
            continue
        vmtype_raw = m.group(1)
        ip = m.group(2)
        
        # ======================== 服务类型映射 ========================
        # 将DNS服务类型映射到实际的目录结构
        type_mapping = {
            'client': 'client',                           # DNS客户端
            'client_chain': 'client',                     # DNS客户端链 -> 使用client目录
            'authorityserver': 'authorityserver',         # 权威服务器
            'authority_chain': 'authorityChainserver',    # 权威链服务器
            'recursionserver': 'recursionserver',         # 递归服务器  
            'recursion_chain': 'recursionNewserver',      # 递归链服务器 -> 使用recursionNewserver
            'rootserver': 'rootserver',                   # 根服务器
            'root_chain': 'rootChainserver'               # 根链服务器
        }
        
        # 根据映射表获取实际目录名
        vmtype = type_mapping.get(vmtype_raw, vmtype_raw)
        local_dir = os.path.join(BASE_UPLOAD_DIR, vmtype, ip)
        if not os.path.isdir(local_dir):
            print(f"本地目录不存在: {local_dir}")
            print(f"跳过VM: {vmtype_raw} ({ip})")
            continue
        for fname in os.listdir(local_dir):
            fpath = os.path.join(local_dir, fname)
            if os.path.isfile(fpath):
                # 构造远程目标路径：/home/类型/IP/文件名
                target_path = f"/root/{fname}"
                builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                
        # break 
                # print(f"  添加上传任务: {fpath} -> {target_path}")
    # 示例：添加命令执行任务
    # 添加一个执行命令任务示例（对第一个VM）
    # if vms:
    #     builder.exectask(device_id=vms[0]["id"], command_str="echo hello > /tmp/hello.txt")
    builder.build_json(OUTPUT_JSON)
    print(f"已生成workflow: {OUTPUT_JSON}")

