from config.config_manager import ConfigManager
from datetime import datetime
import calendar
import requests
from typing import Dict, List

class FlightTasksFixedMonthProcessors:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def process_flight_tasks(self) -> List[Dict]:
        """
        處理固定月份日期爬蟲任務列表

        返回:
            List[Dict]: 處理後的爬蟲任務列表
            範例格式
            [
                {
                    'name': '範例：台北到新加坡 2025-05-19出發 2025-05-20回程',
                    'url_params': {
                        'DepCity1': 'TPE',
                        'ArrCity1': 'SIN',
                        'DepCountry1': 'TW',
                        'ArrCountry1': 'SG',
                        'DepDate1': '21/07/2025',
                        'DepDate2': '27/07/2025',
                        'Rtow': 1
                    }
                }
            ]
        
        Raises:
            requests.RequestException: 當 API 請求失敗時
            ValueError: 當 API 返回的數據格式不正確時
        """
        fixed_month_task_list = self._get_fixed_month_task_list()

        # 儲存處理後的爬蟲任務列表
        processed_flight_tasks = []

        # 將固定月份日期爬蟲任務列表中的任務進行處理
        for task in fixed_month_task_list:
            # 從任務中獲取參數
            month_offset = task["url_params"]["Month"]
            dep_day = int(task["url_params"]["DepDate1"])
            return_day = int(task["url_params"]["DepDate2"])
            
            # 透過 API 計算日期
            date_info = self._calculate_dates_via_api(month_offset, dep_day, return_day)
            
            # 提取 API 返回的資料
            departure_date = date_info["departure_date"]  # YYYY-MM-DD 格式
            return_date = date_info["return_date"]  # YYYY-MM-DD 格式
            target_year = date_info["target_year"]
            target_month = date_info["target_month"]
            
            # 將 YYYY-MM-DD 格式轉換為 DD/MM/YYYY 格式
            dep_date_parts = departure_date.split("-")
            dep_date_str = f"{dep_date_parts[2]}/{dep_date_parts[1]}/{dep_date_parts[0]}"
            
            return_date_parts = return_date.split("-")
            return_date_str = f"{return_date_parts[2]}/{return_date_parts[1]}/{return_date_parts[0]}"
            
            # 建立處理後的任務
            processed_task = task.copy()
            processed_task["url_params"] = task["url_params"].copy()
            
            # 更新任務參數
            processed_task["url_params"]["DepDate1"] = dep_date_str
            processed_task["url_params"]["DepDate2"] = return_date_str
            
            # 移除原始的 Month 參數，因為已經轉換為具體日期
            if "Month" in processed_task["url_params"]:
                del processed_task["url_params"]["Month"]
            
            # 獲取出發和抵達城市
            dep_city = task["url_params"].get("DepCity1", "")
            arr_city = task["url_params"].get("ArrCity1", "")
            
            # 獲取實際使用的日期（從轉換後的字串中提取）
            actual_dep_day = int(dep_date_parts[2])
            actual_return_day = int(return_date_parts[2])
            
            # 更新任務名稱
            processed_task["name"] = f"範例：{dep_city}到{arr_city} {target_year}-{target_month:02d}-{actual_dep_day:02d}出發 {target_year}-{target_month:02d}-{actual_return_day:02d}回程"
            
            processed_flight_tasks.append(processed_task)
            
        return processed_flight_tasks

    def _calculate_dates_via_api(self, month_offset: int, dep_day: int, return_day: int) -> Dict[str, any]:
        """
        透過 API 計算固定月份的日期區間
        
        Args:
            month_offset (int): 月份偏移量，表示從當前月份往後推幾個月
            dep_day (int): 出發日期的天數（1-31）
            return_day (int): 回程日期的天數（1-31）
        
        Returns:
            Dict[str, any]: API 返回的日期資訊，包含以下欄位：
                - departure_date (str): 出發日期，格式為 YYYY-MM-DD
                - return_date (str): 回程日期，格式為 YYYY-MM-DD
                - target_year (int): 目標年份
                - target_month (int): 目標月份
        
        Examples:
            >>> processor = FlightTasksFixedMonthProcessors(config_manager)
            >>> result = processor._calculate_dates_via_api(2, 5, 10)
            >>> result
            {'departure_date': '2025-12-05', 'return_date': '2025-12-10', 'target_year': 2025, 'target_month': 12}
        
        Raises:
            requests.RequestException: 當 API 請求失敗時
            requests.Timeout: 當 API 請求超時時
            ValueError: 當 API 返回錯誤或數據格式不正確時
        """
        # 獲取日期計算 API 配置
        date_api_config = self.config_manager.get_date_api_config()
        endpoint_url = date_api_config.get("endpoint_url")
        timeout = date_api_config.get("timeout", 10)
        auth_token = date_api_config.get("auth_token", "")
        
        if not endpoint_url:
            raise ValueError("日期計算 API 端點 URL 未設置")
        
        # 準備 API 請求參數
        payload = {
            "month_offset": month_offset,
            "dep_day": dep_day,
            "return_day": return_day
        }
        
        # 準備請求標頭
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        try:
            # 發送 API 請求
            response = requests.post(
                url=endpoint_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            # 檢查 HTTP 狀態碼
            if response.status_code != 200:
                error_msg = f"日期計算 API 請求失敗，狀態碼: {response.status_code}，內容: {response.text}"
                raise ValueError(error_msg)
            
            # 解析 JSON 響應
            response_data = response.json()
            
            # 檢查 API 是否返回成功標記
            if not response_data.get("success", False):
                error_msg = response_data.get("error", "未知錯誤")
                raise ValueError(f"日期計算 API 返回錯誤: {error_msg}")
            
            # 檢查是否包含 data 欄位
            if "data" not in response_data:
                raise ValueError("日期計算 API 響應缺少 'data' 欄位")
            
            date_info = response_data["data"]
            
            # 驗證必要欄位
            required_fields = ["departure_date", "return_date", "target_year", "target_month"]
            for field in required_fields:
                if field not in date_info:
                    raise ValueError(f"日期計算 API 響應的 data 欄位缺少 '{field}'")
            
            return date_info
            
        except requests.Timeout as e:
            raise requests.Timeout(f"日期計算 API 請求超時（{timeout}秒）")
        except requests.RequestException as e:
            raise requests.RequestException(f"日期計算 API 請求失敗: {str(e)}")

    def _get_fixed_month_task_list(self) -> List[Dict]:
        """
        獲取固定月份日期爬蟲任務列表

        返回:
            List[Dict]: 固定月份日期爬蟲任務列表
        """
        return self.config_manager.get_flight_tasks_fixed_month()
