from .nodes import LoraBatchUploader

# 定义 NODE_CLASS_MAPPINGS 字典，用于 ComfyUI 识别节点
NODE_CLASS_MAPPINGS = {
    "LoraBatchUploader": LoraBatchUploader
}

# 定义 NODE_DISPLAY_NAME_MAPPINGS 字典，用于在 ComfyUI 界面显示节点名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoraBatchUploader": "Batch Upload LoRA to COS"
}