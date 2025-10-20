from config.config_manager import ConfigManager
from typing import Dict, List
import requests


class DateCalculationService:
    """
    日期計算服務類別
    
    負責呼叫日期計算 API，提供固定月份日期計算和節日日期計算功能。
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化日期計算服務
        
        Args:
            config_manager (ConfigManager): 配置管理器實例
            
        Examples:
            >>> from config.config_manager import ConfigManager
            >>> config_manager = ConfigManager()
            >>> service = DateCalculationService(config_manager)
        
        Raises:
            ValueError: 當 config_manager 為 None 時
        """
        if config_manager is None:
            raise ValueError("config_manager 不能為 None")
        self.config_manager = config_manager
    
    def calculate_fixed_month_dates(
        self, 
        month_offset: int, 
        dep_day: int, 
        return_day: int
    ) -> Dict:
        """
        計算固定月份的航班日期
        
        Args:
            month_offset (int): 月份偏移量，表示從當前月份往後推幾個月，必須大於 0
            dep_day (int): 出發日期的天數 (1-31)
            return_day (int): 回程日期的天數 (1-31)
            
        Returns:
            Dict: 日期資料字典，包含：
                - departure_date (str): 出發日期 (YYYY-MM-DD)
                - return_date (str): 回程日期 (YYYY-MM-DD)
                - target_year (int): 目標年份
                - target_month (int): 目標月份
        
        Examples:
            >>> service.calculate_fixed_month_dates(2, 5, 10)
            {
                'departure_date': '2025-12-05',
                'return_date': '2025-12-10',
                'target_year': 2025,
                'target_month': 12
            }
        
        Raises:
            ValueError: 當月份偏移量小於等於 0 時
            ValueError: 當出發或回程日期天數不在 1-31 範圍內時
            ValueError: 當 API 配置缺失時
            ValueError: 當 API 返回錯誤時
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        # 參數驗證
        self._validate_month_offset(month_offset)
        self._validate_day(dep_day, "出發日期")
        self._validate_day(return_day, "回程日期")
        
        # 獲取 API 配置
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
        
        # 呼叫 API
        return self._call_api(
            api_url=api_url,
            payload=payload,
            timeout=api_config.get('timeout', 30),
            error_message="調用固定月份日期計算 API 失敗"
        )
    
    def calculate_holiday_dates(self, month_offset: int) -> List[Dict]:
        """
        計算指定月份偏移的節日日期
        
        Args:
            month_offset (int): 月份偏移量，表示從當前月份往後推幾個月，必須大於 0
            
        Returns:
            List[Dict]: 節假日資料列表，每個字典包含：
                - holiday_name (str): 節假日名稱
                - holiday_date (str): 節假日日期 (YYYY-MM-DD)
                - departure_date (str): 出發日期 (YYYY-MM-DD)
                - return_date (str): 回程日期 (YYYY-MM-DD)
                - weekday (str): 星期幾
        
        Examples:
            >>> service.calculate_holiday_dates(2)
            [{
                'holiday_name': '行憲紀念日',
                'holiday_date': '2025-12-25',
                'departure_date': '2025-12-21',
                'return_date': '2025-12-25',
                'weekday': '四'
            }]
        
        Raises:
            ValueError: 當月份偏移量小於等於 0 時
            ValueError: 當 API 配置缺失時
            ValueError: 當 API 返回錯誤時
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        # 參數驗證
        self._validate_month_offset(month_offset)
        
        # 獲取 API 配置
        api_config = self.config_manager.get_api_config()
        api_url = api_config.get('holiday_dates_api_url')
        
        if not api_url:
            raise ValueError("配置中缺少 holiday_dates_api_url")
        
        # 準備請求參數
        payload = {
            "month_offset": month_offset
        }
        
        # 呼叫 API
        result = self._call_api(
            api_url=api_url,
            payload=payload,
            timeout=api_config.get('timeout', 30),
            error_message="調用節日日期計算 API 失敗"
        )
        
        # 從結果中提取節假日列表
        holidays = result.get('holidays', [])
        return holidays
    
    def _validate_month_offset(self, month_offset: int) -> None:
        """
        驗證月份偏移量
        
        Args:
            month_offset (int): 月份偏移量
            
        Raises:
            ValueError: 當月份偏移量小於等於 0 時
        """
        if month_offset <= 0:
            raise ValueError(f"月份偏移量必須大於 0，當前值為 {month_offset}")
    
    def _validate_day(self, day: int, field_name: str) -> None:
        """
        驗證日期天數
        
        Args:
            day (int): 日期天數
            field_name (str): 欄位名稱，用於錯誤訊息
            
        Raises:
            ValueError: 當日期天數不在 1-31 範圍內時
        """
        if not (1 <= day <= 31):
            raise ValueError(f"{field_name}天數必須在 1-31 之間，當前值為 {day}")
    
    def _call_api(
        self, 
        api_url: str, 
        payload: Dict, 
        timeout: int,
        error_message: str
    ) -> Dict:
        """
        呼叫日期計算 API
        
        Args:
            api_url (str): API URL
            payload (Dict): 請求參數
            timeout (int): 請求超時時間（秒）
            error_message (str): 錯誤訊息前綴
            
        Returns:
            Dict: API 返回的資料
            
        Raises:
            ValueError: 當 API 返回錯誤時
            requests.exceptions.RequestException: 當 API 請求失敗時
        """
        try:
            # 發送 POST 請求
            response = requests.post(
                api_url,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            
            # 解析響應
            result = response.json()
            
            # 檢查 API 是否返回成功
            if not result.get('success'):
                error_msg = result.get('error', '未知錯誤')
                raise ValueError(f"API 返回錯誤: {error_msg}")
            
            # 返回資料部分
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(f"{error_message}: {str(e)}")
