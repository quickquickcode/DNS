import json
import os

import json
import uuid
import base64
from pathlib import Path


# === 默认参数，可由外部main传入 ===
TOPO_FILE = None
TARGET_VM_SERVICE_KEY = None

class WorkflowBuilder:
    def exectask(self, device_id, command_str):
        """添加执行命令任务，命令字符串自动base64编码"""
        vm = next((v for v in self.vms if v['id'] == device_id), None)
        if not vm:
            raise ValueError(f"未找到设备id={device_id}的VM")
        # base64编码命令
        encoded_cmd = base64.b64encode(command_str.encode('utf-8')).decode('utf-8')
        self.tasks.append({
            "device_id": device_id,
            "device_name": vm['name'],
            "ip": vm['ip'],
            "file_path": None,
            "target_path": None,
            "exec_base64_cmd": encoded_cmd
        })
    def __init__(self):
        self.topo_data = None
        self.vms = []
        self.tasks = []  # 每个task: {"device_id", "device_name", "ip", "file_path", "target_path"}

    def loadfile(self, topo_file, vm_service_key):
        """加载topo文件并筛选目标VM"""
        self.topo_data = None
        self.vms = []
        self.tasks = []
        with open(topo_file, 'r', encoding='utf-8') as f:
            self.topo_data = json.load(f)
        self.vms = self._extract_target_vms(self.topo_data, vm_service_key)
        return self.vms

    def appendtask(self, device_id, file_path, target_path):
        """添加上传任务"""
        vm = next((v for v in self.vms if v['id'] == device_id), None)
        if not vm:
            raise ValueError(f"未找到设备id={device_id}的VM")
        self.tasks.append({
            "device_id": device_id,
            "device_name": vm['name'],
            "ip": vm['ip'],
            "file_path": file_path,
            "target_path": target_path
        })

    def build_json(self, output_path):
        """生成串联所有任务的workflow json"""
        if not self.tasks:
            raise ValueError("未添加任何任务")
        # 只检查有 file_path 的任务文件是否存在
        missing_files = [task['file_path'] for task in self.tasks if task.get('file_path') and not os.path.isfile(task['file_path'])]
        if missing_files:
            print("以下文件不存在，无法生成json：")
            for f in missing_files:
                print(f"  - {f}")
            raise FileNotFoundError("部分上传文件不存在，请检查路径！")
        start_id = generate_id()
        stop_id = generate_id()
        nodeList = [
            {"type": "START", "name": "开始", "id": start_id, "x": 0, "y": 0, "width": 50, "length": 50, "layer": 1, "autoStart": True, "autoStop": True, "preCondition": "ALL"}
        ]
        linkList = []
        tracList = []
        prev_node_id = start_id
        x_pos = 150
        for task in self.tasks:
            node_id = generate_id()
            trac_id = generate_id()
            if task.get('file_path') and task.get('target_path'):
                # 上传文件任务
                encoded = encode_file_to_base64(task['file_path'])
                nodeList.append({
                    "type": "TRAC", "name": f"上传配置到 {task['ip']}", "id": node_id, "x": x_pos, "y": 0, "width": 50, "length": 50, "layer": 1, "autoStart": True, "autoStop": True, "preCondition": "ALL"
                })
                linkList.append({"id": generate_id(), "source": prev_node_id, "target": node_id, "type": "SEQ"})
                tracList.append({
                    "metadata": {
                        "arg": [],
                        "cmd": generate_base64_command(task['target_path'], encoded),
                        "env": []
                    },
                    "description": "Base64配置上传",
                    "type": "EXEC_CMD",
                    "execType":"ssh",
                    "deviceId": task["device_id"],
                    "deviceName": task["device_name"],
                    "mode": "PROCESS",
                    "id": trac_id,
                    "deviceType": "VM",
                    "parentId": node_id,
                    "timelimit": 20,
                    "name": "上传配置",
                    "category": "ENV"
                })
            elif task.get('exec_base64_cmd'):
                # 执行命令任务
                nodeList.append({
                    "type": "TRAC", "name": f"执行命令到 {task['ip']}", "id": node_id, "x": x_pos, "y": 0, "width": 50, "length": 50, "layer": 1, "autoStart": True, "autoStop": True, "preCondition": "ALL"
                })
                linkList.append({"id": generate_id(), "source": prev_node_id, "target": node_id, "type": "SEQ"})
                tracList.append({
                    "metadata": {
                        "arg": [],
                        "cmd": f"echo {task['exec_base64_cmd']} | base64 -d | bash",
                        "env": []
                    },
                    "description": "Base64命令执行",
                    "type": "EXEC_CMD",
                    "execType":"ssh",
                    "deviceId": task["device_id"],
                    "deviceName": task["device_name"],
                    "mode": "PROCESS",
                    "id": trac_id,
                    "deviceType": "VM",
                    "parentId": node_id,
                    "timelimit": 20,
                    "name": "执行命令",
                    "category": "ENV"
                })
            else:
                continue
            prev_node_id = node_id
            x_pos += 25
        nodeList.append({"type": "STOP", "name": "结束", "id": stop_id, "x": x_pos, "y": 0, "width": 50, "length": 50, "layer": 1, "autoStart": True, "autoStop": True, "preCondition": "ALL"})
        linkList.append({"id": generate_id(), "source": prev_node_id, "target": stop_id, "type": "SEQ"})
        total_json = {
            "fromJson": True,
            "replaceDeviceId": False,
            "templateData": {
                "neventList": [
                    {"name": "开始", "id": start_id, "type": "START"},
                    {"name": "结束", "id": stop_id, "type": "STOP"}
                ],
                "nodeList": nodeList,
                "linkList": linkList,
                "tracList": tracList
            }
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(total_json, f, indent=2, ensure_ascii=False)
        print(f"✅ 已生成workflow: {output_path}")

    @staticmethod
    def _extract_target_vms(data, vm_service_key=None):
        vms = []
        try:
            position_topos = data["fileData"]["otherData"]["positionTopos"]
        except Exception as e:
            print("解析positionTopos失败:", e)
            return []
        for item in position_topos:
            if item.get("type") == "VM" and item.get("vmType") in ("SERVER", "CLIENT"):
                vms.append({
                    "id": item["id"],
                    "name": item.get("name", ""),
                    "ip": item.get("rangeName", ""),
                    "service_type": None
                })
        return vms

# === 工具函数 ===
def generate_id():
    return uuid.uuid4().hex

def encode_file_to_base64(file_path):
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def generate_base64_command(target_path, base64_content):
    dir_path = os.path.dirname(target_path)
    # return f"echo {base64_content} | base64 -d > {target_path} && chmod +x {target_path}"
    # 不使用管道符，使用here document方式
    return f'base64 -d > {target_path} << EOF\n{base64_content}\nEOF\nchmod +x {target_path}'

def extract_target_vms(data):
    # 适配topo_test8.json结构，所有type为VM且vmType为SERVER的都生成配置
    vms = []
    try:
        position_topos = data["fileData"]["otherData"]["positionTopos"]
    except Exception as e:
        print("解析positionTopos失败:", e)
        return []
    for item in position_topos:
        if item.get("type") == "VM" and item.get("vmType") == "SERVER":
            # 兼容service_type字段在otherAttributeIns、顶层和name字段，模糊匹配且不区分大小写
            service_type = None
            for attr in item.get("otherAttributeIns", []):
                if attr.get("key", "").lower() == "service_type":
                    service_type = attr.get("value", "")
                    break
            if (not service_type) and "service_type" in item:
                service_type = str(item["service_type"])
            name = item.get("name", "")
            # 只要service_type或name字段包含关键字即可
            if (
                (service_type and TARGET_VM_SERVICE_KEY.lower() in service_type.lower())
                or (name and TARGET_VM_SERVICE_KEY.lower() in name.lower())
            ):
                vms.append({
                    "id": item["id"],
                    "name": name,
                    "ip": item.get("rangeName", ""),
                    "service_type": service_type
                })
    print("[调试] 匹配到的VM节点如下：")
    for vm in vms:
        print(f"id={vm['id']} | name={vm['name']} | ip={vm['ip']} | service_type={vm['service_type']}")
    return vms

def generate_vm_config(vm, encoded_files):
    start_id = generate_id()
    upload_node_id = generate_id()
    stop_id = generate_id()
    trac_id = generate_id()

    return {
        "fromJson": True,
        "replaceDeviceId": False,
        "templateData": {
            "neventList": [
                {"name": "开始", "id": start_id, "type": "START"},
                {"name": "结束", "id": stop_id, "type": "STOP"}
            ],
            "nodeList": [
                {"type": "START", "name": "开始", "id": start_id, "x": 0, "y": 0, "width": 50, "length": 50, "layer": 1, "autoStart": True, "autoStop": True, "preCondition": "ALL"},
                {"type": "TRAC", "name": f"上传配置到 {vm['ip']}", "id": upload_node_id, "x": 150, "y": 0, "width": 50, "length": 50, "layer": 1, "autoStart": True, "autoStop": True, "preCondition": "ALL"},
                {"type": "STOP", "name": "结束", "id": stop_id, "x": 300, "y": 0, "width": 50, "length": 50, "layer": 1, "autoStart": True, "autoStop": True, "preCondition": "ALL"},
            ],
            "linkList": [
                {"id": generate_id(), "source": start_id, "target": upload_node_id, "type": "SEQ"},
                {"id": generate_id(), "source": upload_node_id, "target": stop_id, "type": "SEQ"}
            ],
            "tracList": [
                {
                    "metadata": {
                        "arg": [],
                        "cmd": generate_base64_command(TARGET_PATH, encoded_files),
                        "env": []
                    },
                    "description": "Base64配置上传",
                    "type": "EXEC_CMD",
                    "execType":"ssh",
                    "deviceId": vm["id"],
                    "deviceName": vm["ip"],
                    "mode": "PROCESS",
                    "id": trac_id,
                    "deviceType": "VM",
                    "parentId": upload_node_id,
                    "timelimit": 20,
                    "name": "上传配置",
                    "category": "ENV"
                }
            ]
        }
    }


