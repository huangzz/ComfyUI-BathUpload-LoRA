import os
import time
import logging
from nodes import *
from qcloud_cos import CosConfig, CosS3Client, CosClientError, CosServiceError

# 日志配置
logging.basicConfig(level=logging.DEBUG, 
                    format='[%(asctime)s][%(levelname)s] %(message)s',
                    handlers=[
                        logging.FileHandler("lora_uploader.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger("LoraUploader")

# 常量配置
REGION = 'ap-shanghai'
BUCKET = 'lora-1321071370'
HISTORY_FILE = "upload_history.txt"
MAX_RETRIES = 3
RETRY_DELAY = 5

class LoraBatchUploader:
    def __init__(self):
        self.uploaded_files = set()
        self.load_history()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "secret_id": ("STRING", {"default": ""}),
                "secret_key": ("STRING", {"default": ""}),
                "force_upload": ("BOOLEAN", {"default": False}),
                "retry_times": ("INT", {"default": 3, "min": 0, "max": 10}),
            },
            "optional": {
                "exclude_list": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "execute_upload"
    CATEGORY = "AI/IO"
    OUTPUT_NODE = True

    def load_history(self):
        """加载上传历史记录"""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r") as f:
                    self.uploaded_files = {line.strip() for line in f if line.strip()}
                logger.debug(f"Loaded {len(self.uploaded_files)} history records")
        except Exception as e:
            logger.error(f"加载历史记录失败: {str(e)}")

    def save_history(self):
        """保存上传历史"""
        try:
            with open(HISTORY_FILE, "w") as f:
                f.write("\n".join(sorted(self.uploaded_files)))
            logger.debug("历史记录保存成功")
        except Exception as e:
            logger.error(f"保存历史记录失败: {str(e)}")

    def execute_upload(self, secret_id, secret_key, force_upload, retry_times, exclude_list=""):
        try:
            # 初始化COS客户端
            logger.info("正在初始化COS客户端...")
            cos_config = CosConfig(Region=REGION, SecretId=secret_id, SecretKey=secret_key)
            cos_client = CosS3Client(cos_config)

            # 获取Lora根目录
            lora_base = folder_paths.get_folder_paths("loras")[0]
            logger.info(f"基础目录: {lora_base}")

            # 生成排除列表
            exclude_files = self.parse_exclude_list(exclude_list, lora_base)
            logger.debug(f"排除列表: {exclude_files}")

            # 扫描文件
            logger.info("开始扫描文件...")
            file_list = self.scan_all_files(lora_base, exclude_files)
            logger.info(f"找到 {len(file_list)} 个待处理文件")

            # 执行上传
            results = self.process_uploads(cos_client, lora_base, file_list, force_upload, retry_times)

            # 生成报告
            report = self.generate_upload_report(results)
            return {"ui": report, "result": ()}

        except Exception as e:
            logger.exception("主流程异常")
            return {"ui": {"error": str(e)}, "result": ()}

    def parse_exclude_list(self, exclude_list, base_dir):
        """解析排除列表为绝对路径"""
        exclude_files = set()
        for line in exclude_list.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # 转换为绝对路径
            if os.path.isabs(line):
                abs_path = line
            else:
                abs_path = os.path.normpath(os.path.join(base_dir, line))
            
            exclude_files.add(abs_path.lower())
            logger.debug(f"添加到排除列表: {abs_path}")
        
        return exclude_files

    def scan_all_files(self, base_dir, exclude_files):
        """递归扫描所有文件"""
        valid_ext = ('.safetensors', '.ckpt')
        file_list = []

        for root, dirs, files in os.walk(base_dir):
            # 取消目录过滤
            for file in files:
                file_path = os.path.join(root, file)
                if file.lower().endswith(valid_ext):
                    # 检查排除列表
                    if file_path.lower() in exclude_files:
                        logger.debug(f"排除文件: {file_path}")
                        continue
                    file_list.append(file_path)
                    logger.debug(f"发现有效文件: {file_path}")
                else:
                    logger.debug(f"跳过非Lora文件: {file_path}")
        
        return file_list

    def process_uploads(self, cos_client, base_dir, file_list, force_upload, max_retries):
        """处理上传流程"""
        results = {'success': [], 'failed': []}
        
        for file_path in file_list:
            rel_path = os.path.relpath(file_path, base_dir)
            logger.info(f"处理文件: {rel_path}")

            # 检查上传历史
            if not force_upload and rel_path in self.uploaded_files:
                logger.info(f"跳过已上传文件: {rel_path}")
                continue

            # 执行上传
            success = self.upload_with_retries(cos_client, file_path, rel_path, max_retries)
            
            if success:
                self.uploaded_files.add(rel_path)
                results['success'].append(rel_path)
                logger.info(f"上传成功: {rel_path}")
            else:
                results['failed'].append(rel_path)
                logger.error(f"上传失败: {rel_path}")

        self.save_history()
        return results

    def upload_with_retries(self, cos_client, local_path, cos_key, max_retries):
        """带重试的上传逻辑"""
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"上传尝试 {attempt+1}/{max_retries+1}: {cos_key}")
                response = cos_client.upload_file(
                    Bucket=BUCKET,
                    LocalFilePath=local_path,
                    Key=cos_key,
                    EnableMD5=True
                )
                logger.debug(f"上传响应: {response}")
                return True
            except CosClientError as e:
                logger.error(f"客户端错误: {str(e)}")
            except CosServiceError as e:
                logger.error(f"服务端错误: [{e.get_error_code()}] {e.get_error_msg()}")
            except Exception as e:
                logger.error(f"意外错误: {str(e)}")
            
            if attempt < max_retries:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.info(f"{wait_time}秒后重试...")
                time.sleep(wait_time)
        
        return False

    def generate_upload_report(self, results):
        """生成上传报告"""
        success_num = len(results['success'])
        failed_num = len(results['failed'])
        
        report = {
            "message": f"成功: {success_num} | 失败: {failed_num}",
            "details": {
                "success": results['success'],
                "failed": results['failed']
            }
        }
        
        logger.info(f"上传报告: {report['message']}")
        return report

NODE_CLASS_MAPPINGS = {"LoraBatchUploader": LoraBatchUploader}
NODE_DISPLAY_NAME_MAPPINGS = {"LoraBatchUploader": "🚩 高级Lora上传器"}