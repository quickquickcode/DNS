from config import WorkflowBuilder

# ======================== 配置参数 ========================
# 拓扑数据文件路径 - 包含网络节点和服务信息的JSON文件
TOPO_PATH = "./01源文件/99/topoData_99_上传.json"
TOPO_PATH = "./01源文件/99/子网ip1_formatted_20250806_223246.json"
TOPO_PATH = "./01源文件/99/topoData_99_8-25.json"
TOPO_PATH = "./01源文件/99/topoData_99_new_images.json"

# TOPO_PATH = "./01源文件/99/test_biaozhun_topo.json"
# TOPO_PATH = "子网ip1_topo.json"
# TOPO_PATH = "1000/topoData_1000_上传.json"
# # TOPO_PATH = "./06/129-测试-sss_forma.json"
# TOPO_PATH = "./01源文件/1000-2/topoData_1000_上传.json"
# TOPO_PATH = "./01源文件/1000/topoData_1000_上传.json"
# TOPO_PATH = "./01源文件/2000/topoData_2000_上传.json"

# 目标服务类型 - 指定要处理的DNS服务类型
# 
SERVICE_KEY = "gzdx_dns_client_0.7"

# 输出工作流文件路径 - 生成的workflow JSON文件保存位置
# OUTPUT_JSON = "01源文件/1000/workflow_demo_1000.json"
OUTPUT_JSON = "01源文件/99/workflow_demo_99.json"
OUTPUT_JSON = "01源文件/99/workflow_topoData_99_9_1.json"



# 源文件基础目录 - 本地存储DNS配置文件的根目录
BASE_UPLOAD_DIR = "01源文件/99/DNS_99_y/DNS_99_y"
# BASE_UPLOAD_DIR = "1000/DNS_1000_y/DNS_1000_y"
# BASE_UPLOAD_DIR = "01源文件/1000/DNS_2025-07-22_16-45-23_436/DNS_2025-07-22_16-45-23_436"
# BASE_UPLOAD_DIR = "./01源文件/2000/DNS_2000"


# ======================== 主程序 ========================
# gzdx_dns_client_chain_0.2 无需导入是正常现象
times = 0

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
            continue
        
        # 🔥 重要修改：对每个文件单独创建一个文件导入任务
        files = os.listdir(local_dir)
        print(f"VM {ip} ({vmtype}) 发现 {len(files)} 个文件:")
        
        # 特殊处理 authorityChainserver 类型
        if vmtype == 'authorityChainserver':
            # 根据 up.sh 脚本分析，文件应该上传到特定位置
            file_mapping = {
                'named.conf': '/root/named.conf',
                'xdeos.com.zone': '/root/named/xdeos.com.zone',
                'up.sh': '/root/up.sh',
                'tasks.xml': '/root/tasks.xml',
                'xdeos.com.zone-cold': '/root/xdeos.com.zone-cold'
            }
            
            # 首先上传所有文件到 /root/ 目录（up.sh 脚本工作目录）
            for fname in files:
                fpath = os.path.join(local_dir, fname)
                if os.path.isfile(fpath):
                    target_path = f"/root/{fname}"
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 上传文件: {fname} -> {target_path}")
            
            # 然后执行 up.sh 脚本进行自动部署
            deploy_command = "cd /root && chmod +x up.sh && ./up.sh"
            builder.exectask(device_id=vm["id"], command_str=deploy_command)
            print(f"  🚀 执行部署脚本: {deploy_command}")
            
        # 特殊处理 authorityserver 类型
        elif vmtype == 'authorityserver':
            # 根据 up.sh 脚本分析，authorityserver 处理 itau.cn 域名
            # up.sh 脚本会将文件部署到：
            # - named.conf -> /root/named.conf
            # - *.zone -> /root/named/*.zone（例如 itau.cn.zone）
            
            # 首先上传所有文件到 /root/ 目录（up.sh 脚本工作目录）
            for fname in files:
                fpath = os.path.join(local_dir, fname)
                if os.path.isfile(fpath):
                    target_path = f"/root/{fname}"
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 上传文件: {fname} -> {target_path}")
            
            # 然后执行 up.sh 脚本进行自动部署
            deploy_command = "cd /root && chmod +x up.sh && ./up.sh"
            builder.exectask(device_id=vm["id"], command_str=deploy_command)
            print(f"  🚀 执行部署脚本: {deploy_command}")
            
        # 特殊处理 client 类型
        elif vmtype == 'client':
            # 根据 up.sh 脚本分析，client 包含多种功能：
            # - DNS解析配置: resolv.conf -> /root/resolv.conf
            # - Go程序: dig.go, rootDig.go, authoDig.go 等
            # - 压测脚本: ddos_start.sh, pressRoot_start.sh 等
            # - 配置文件: address, pressRootAddress 等
            
            # 首先上传所有文件到 /root/ 目录（up.sh 脚本工作目录）
            for fname in files:
                fpath = os.path.join(local_dir, fname)
                if os.path.isfile(fpath):
                    target_path = f"/root/{fname}"
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 上传文件: {fname} -> {target_path}")
            
            # 然后执行 up.sh 脚本进行自动部署
            # up.sh 会完成以下任务：
            # 1. 配置DNS解析器 (resolv.conf)
            # 2. 编译并启动Go程序 (dig.go)
            # 3. 设置开机自启动
            # 4. 配置网络接口参数
            deploy_command = "cd /root && chmod +x up.sh && ./up.sh"
            builder.exectask(device_id=vm["id"], command_str=deploy_command)
            print(f"  🚀 执行部署脚本: {deploy_command}")
            
        # 特殊处理 recursionNewserver 类型
        elif vmtype == 'recursionNewserver':
            # 根据 up.sh 脚本分析，recursionNewserver 是递归DNS服务器
            # up.sh 脚本会将文件部署到：
            # - named.conf -> /root/named.conf (递归服务器配置，recursion yes)
            # - root.ca -> /root/named/root.ca (根域提示文件)
            
            # 首先上传所有文件到 /root/ 目录（up.sh 脚本工作目录）
            for fname in files:
                fpath = os.path.join(local_dir, fname)
                if os.path.isfile(fpath):
                    target_path = f"/root/{fname}"
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 上传文件: {fname} -> {target_path}")
            
            # 然后执行 up.sh 脚本进行自动部署
            deploy_command = "cd /root && chmod +x up.sh && ./up.sh"
            builder.exectask(device_id=vm["id"], command_str=deploy_command)
            print(f"  🚀 执行部署脚本: {deploy_command}")
            
        # 特殊处理 recursionserver 类型
        elif vmtype == 'recursionserver':
            # 根据 up.sh 脚本分析，recursionserver 是标准递归DNS服务器
            # 与 recursionNewserver 类似，但包含额外的链式配置
            # up.sh 脚本会将文件部署到：
            # - named.conf -> /root/named.conf (递归服务器配置，recursion yes)
            # - root.ca -> /root/named/root.ca (根域提示文件，包含多个根服务器)
            # - root.ca-chain -> /root/named/root.ca-chain (链式根域配置备份)
            
            # 首先上传所有文件到 /root/ 目录（up.sh 脚本工作目录）
            for fname in files:
                fpath = os.path.join(local_dir, fname)
                if os.path.isfile(fpath):
                    target_path = f"/root/{fname}"
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 上传文件: {fname} -> {target_path}")
            
            # 然后执行 up.sh 脚本进行自动部署
            deploy_command = "cd /root && chmod +x up.sh && ./up.sh"
            builder.exectask(device_id=vm["id"], command_str=deploy_command)
            print(f"  🚀 执行部署脚本: {deploy_command}")
            
        # 特殊处理 rootChainserver 类型
        elif vmtype == 'rootChainserver':
            # 根据 up.sh 脚本分析，rootChainserver 是根DNS链服务器
            # up.sh 脚本会将文件部署到：
            # - named.conf -> /root/named.conf (根服务器配置，recursion no)
            # - root.zone -> /root/named/root.zone (根区域文件，包含顶级域委派)
            # 附加功能：
            # - Timepull.sh (定时拉取根区域更新脚本)
            # - Gen-base-org-test.json (根区域生成配置)
            
            # 首先上传所有文件到 /root/ 目录（up.sh 脚本工作目录）
            for fname in files:
                fpath = os.path.join(local_dir, fname)
                if os.path.isfile(fpath):
                    target_path = f"/root/{fname}"
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 上传文件: {fname} -> {target_path}")
            
            # 然后执行 up.sh 脚本进行自动部署
            deploy_command = "cd /root && chmod +x up.sh && chmod +x Timepull.sh && ./up.sh"
            builder.exectask(device_id=vm["id"], command_str=deploy_command)
            print(f"  🚀 执行部署脚本: {deploy_command}")
            
        # 特殊处理 rootserver 类型
        elif vmtype == 'rootserver':
            # 根据 up.sh 脚本分析，rootserver 是标准根DNS服务器
            # 与 rootChainserver 类似，但支持主从同步机制
            # up.sh 脚本会将文件部署到：
            # - named.conf -> /root/named.conf (根服务器配置，包含主从同步设置)
            # - root.zone -> /root/named/root.zone (根区域文件，包含所有根服务器和顶级域)
            # 主从同步特性：
            # - 支持 DNS NOTIFY 机制
            # - 配置 allow-transfer 和 also-notify
            # - 多根服务器协同工作
            
            # 首先上传所有文件到 /root/ 目录（up.sh 脚本工作目录）
            for fname in files:
                fpath = os.path.join(local_dir, fname)
                if os.path.isfile(fpath):
                    target_path = f"/root/{fname}"
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 上传文件: {fname} -> {target_path}")
            
            # 然后执行 up.sh 脚本进行自动部署
            deploy_command = "cd /root && chmod +x up.sh && ./up.sh"
            builder.exectask(device_id=vm["id"], command_str=deploy_command)
            print(f"  🚀 执行部署脚本: {deploy_command}")
            
        else:
            # 其他类型保持原有逻辑
            for fname in files:
                fpath = os.path.join(local_dir, fname)
                if os.path.isfile(fpath):
                    # 构造远程目标路径：/home/类型/IP/文件名
                    target_path = f"/root/{fname}"
                    
                    # 🔥 关键：每个文件单独创建一个导入任务
                    builder.appendtask(device_id=vm["id"], file_path=fpath, target_path=target_path)
                    print(f"  ✅ 单独任务: {fname} -> {target_path}")
                    times += 1
    # 示例：添加命令执行任务
    # 添加一个执行命令任务示例（对第一个VM）
    # if vms:
    #     builder.exectask(device_id=vms[0]["id"], command_str="echo hello > /tmp/hello.txt")
    builder.build_json(OUTPUT_JSON)
    print(f"已生成workflow: {OUTPUT_JSON}")
    print(f"总共添加了 {times} 个文件导入任务")

