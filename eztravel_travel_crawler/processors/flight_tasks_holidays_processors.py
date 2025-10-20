from config.config_manager import ConfigManager
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Dict, List
from services.date_calculation_service import DateCalculationService

class FlightTasksHolidaysProcessors:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.date_service = DateCalculationService(config_manager)

    def process_flight_tasks(self) -> List[Dict]:
        """
        處理節日爬蟲任務列表

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
            ValueError: 當 API 配置缺失時
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        # 獲取基礎任務列表
        holidays_task_list = self._get_holidays_task_list()
        
        # 處理後的任務列表
        processed_flight_tasks = []
        
        # 遍歷每個基礎任務
        for base_task in holidays_task_list:
            # 根據任務中的 Month 參數調用 API
            month_offset = base_task["url_params"]["Month"]
            
            # 調用日期計算服務獲取節假日資料
            holidays_data = self.date_service.calculate_holiday_dates(month_offset)
            
            # 遍歷 API 返回的每個節假日
            for holiday in holidays_data:
                # 解析 API 返回的日期
                dep_date = datetime.strptime(holiday['departure_date'], "%Y-%m-%d")
                ret_date = datetime.strptime(holiday['return_date'], "%Y-%m-%d")
                
                processed_task = deepcopy(base_task)
                
                # 格式化日期為 DD/MM/YYYY
                dep_date_str = dep_date.strftime("%d/%m/%Y")
                ret_date_str = ret_date.strftime("%d/%m/%Y")
                
                # 更新任務參數
                processed_task["url_params"]["DepDate1"] = dep_date_str
                processed_task["url_params"]["DepDate2"] = ret_date_str
                
                # 移除原始的 Month 參數，因為已經轉換為具體日期
                if "Month" in processed_task["url_params"]:
                    del processed_task["url_params"]["Month"]
                
                # 生成任務名稱
                dep_city = base_task["url_params"].get("DepCity1", "")
                arr_city = base_task["url_params"].get("ArrCity1", "")
                holiday_name = holiday['holiday_name']
                
                processed_task["name"] = f"{dep_city}到{arr_city} {holiday_name} {dep_date.strftime('%Y-%m-%d')}出發 {ret_date.strftime('%Y-%m-%d')}回程"
                
                processed_flight_tasks.append(processed_task)
                    
        return processed_flight_tasks
    

    def _get_holidays_task_list(self) -> List[Dict]:
        """
        獲取節日爬蟲任務列表

        Returns:
            List[Dict]: 節日爬蟲任務列表
        
        Examples:
            >>> processor._get_holidays_task_list()
            [{
                'name': '範例： 四個月後的台北到新加坡節日',
                'url_params': {
                    'Month': 4,
                    'DepCity1': 'TPE',
                    'ArrCity1': 'SIN',
                    ...
                }
            }]
        
        Raises:
            ValueError: 當配置尚未加載時
        """
        return self.config_manager.get_flight_tasks_holidays()
 