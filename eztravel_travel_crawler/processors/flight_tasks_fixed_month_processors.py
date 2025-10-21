from config.config_manager import ConfigManager
from copy import deepcopy
from datetime import datetime
from typing import Dict, List
from services.date_calculation_service import DateCalculationService

class FlightTasksFixedMonthProcessors:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.date_service = DateCalculationService(config_manager)

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
            
            # 調用日期計算服務獲取日期資料
            date_data = self.date_service.calculate_fixed_month_dates(
                month_offset, dep_day, return_day
            )
            
            # 解析 API 返回的日期 (YYYY-MM-DD 格式)
            dep_date = datetime.strptime(date_data['departure_date'], "%Y-%m-%d")
            ret_date = datetime.strptime(date_data['return_date'], "%Y-%m-%d")
            
            processed_task = deepcopy(task)
            
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
