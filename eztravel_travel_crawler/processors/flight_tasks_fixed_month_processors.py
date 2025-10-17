from config.config_manager import ConfigManager
from datetime import datetime
from typing import Dict, List
import requests

class FlightTasksFixedMonthProcessors:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def process_flight_tasks(self) -> List[Dict]:
        """
        處理固定月份日期爬蟲任務列表

        Returns:
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
            ValueError: 當 API 配置缺失時
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        fixed_month_task_list = self._get_fixed_month_task_list()

        # 儲存處理後的爬蟲任務列表
        processed_flight_tasks = []

        # 將固定月份日期爬蟲任務列表中的任務進行處理
        for task in fixed_month_task_list:
            # 根據任務中的參數調用 API
            month_offset = task["url_params"]["Month"]
            dep_day = int(task["url_params"]["DepDate1"])
            return_day = int(task["url_params"]["DepDate2"])
            
            # 調用 API 獲取日期資料
            date_data = self._fetch_dates_from_api(month_offset, dep_day, return_day)
            
            # 解析 API 返回的日期 (YYYY-MM-DD 格式)
            dep_date = datetime.strptime(date_data['departure_date'], "%Y-%m-%d")
            ret_date = datetime.strptime(date_data['return_date'], "%Y-%m-%d")
            
            processed_task = task.copy()
            processed_task["url_params"] = task["url_params"].copy()
            
            # 格式化日期為 DD/MM/YYYY
            dep_date_str = dep_date.strftime("%d/%m/%Y")
            return_date_str = ret_date.strftime("%d/%m/%Y")
            
            # 更新任務參數
            processed_task["url_params"]["DepDate1"] = dep_date_str
            processed_task["url_params"]["DepDate2"] = return_date_str
            
            # 移除原始的 Month 參數，因為已經轉換為具體日期
            if "Month" in processed_task["url_params"]:
                del processed_task["url_params"]["Month"]
            
            dep_city = task["url_params"].get("DepCity1", "")
            arr_city = task["url_params"].get("ArrCity1", "")
            
            # 生成任務名稱 (保持與原先相同的格式)
            processed_task["name"] = f"範例：{dep_city}到{arr_city} {dep_date.strftime('%Y-%m-%d')}出發 {ret_date.strftime('%Y-%m-%d')}回程"
            
            processed_flight_tasks.append(processed_task)
            
        return processed_flight_tasks

    def _fetch_dates_from_api(self, month_offset: int, dep_day: int, return_day: int) -> Dict:
        """
        從固定月份日期計算 API 獲取日期資料
        
        Args:
            month_offset (int): 月份偏移量，表示從當前月份往後推幾個月
            dep_day (int): 出發日期的天數 (1-31)
            return_day (int): 回程日期的天數 (1-31)
            
        Returns:
            Dict: 日期資料字典，包含：
                - departure_date (str): 出發日期 (YYYY-MM-DD)
                - return_date (str): 回程日期 (YYYY-MM-DD)
                - target_year (int): 目標年份
                - target_month (int): 目標月份
        
        Examples:
            >>> processor._fetch_dates_from_api(2, 5, 10)
            {
                'departure_date': '2025-12-05',
                'return_date': '2025-12-10',
                'target_year': 2025,
                'target_month': 12
            }
        
        Raises:
            ValueError: 當 API 配置缺失或參數無效時
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        if month_offset < 0:
            raise ValueError(f"月份偏移量必須大於等於 0，當前值為 {month_offset}")
        
        if not (1 <= dep_day <= 31):
            raise ValueError(f"出發日期天數必須在 1-31 之間，當前值為 {dep_day}")
        
        if not (1 <= return_day <= 31):
            raise ValueError(f"回程日期天數必須在 1-31 之間，當前值為 {return_day}")
        
        # 從配置中獲取 API URL
        api_config = self.config_manager.get_api_config()
        api_url = api_config.get('fixed_month_dates_api_url')
        
        if not api_url:
            raise ValueError("配置中缺少 fixed_month_dates_api_url")
        
        # 準備請求參數
        payload = {
            "month_offset": month_offset,
            "dep_day": dep_day,
            "return_day": return_day
        }
        
        try:
            # 調用 API
            response = requests.post(
                api_url,
                json=payload,
                timeout=api_config.get('timeout', 30)
            )
            response.raise_for_status()
            
            # 解析響應
            result = response.json()
            
            if not result.get('success'):
                error_msg = result.get('error', '未知錯誤')
                raise ValueError(f"API 返回錯誤: {error_msg}")
            
            # 返回日期資料
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"調用固定月份日期計算 API 失敗: {str(e)}"
            )

    def _get_fixed_month_task_list(self) -> List[Dict]:
        """
        獲取固定月份日期爬蟲任務列表

        Returns:
            List[Dict]: 固定月份日期爬蟲任務列表
        
        Examples:
            >>> processor._get_fixed_month_task_list()
            [{
                'name': '範例： 兩個月後的台北到新加坡該月5號出發10號回程',
                'url_params': {
                    'Month': 2,
                    'DepCity1': 'TPE',
                    'ArrCity1': 'SIN',
                    ...
                }
            }]
        
        Raises:
            ValueError: 當配置尚未加載時
        """
        return self.config_manager.get_flight_tasks_fixed_month()
