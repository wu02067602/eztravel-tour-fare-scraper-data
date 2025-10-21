from config.config_manager import ConfigManager
from typing import Dict, List
import requests


class HolidayCalculationService:
    """
    節日計算服務類別
    
    負責呼叫節日日期計算 API，提供節日相關日期計算功能。
    專門處理節假日的日期計算，包括出發日期和回程日期的計算。
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化節日計算服務
        
        Args:
            config_manager (ConfigManager): 配置管理器實例
            
        Examples:
            >>> from config.config_manager import ConfigManager
            >>> config_manager = ConfigManager()
            >>> service = HolidayCalculationService(config_manager)
        
        Raises:
            ValueError: 當 config_manager 為 None 時
        """
        if config_manager is None:
            raise ValueError("config_manager 不能為 None")
        self.config_manager = config_manager
    
    def calculate_holiday_dates(self, month_offset: int) -> List[Dict]:
        """
        計算指定月份偏移的節日日期
        
        透過呼叫外部 API，根據月份偏移量獲取該月份內的所有節假日資訊，
        包括節日名稱、日期以及建議的航班出發和回程日期。
        
        Args:
            month_offset (int): 月份偏移量，表示從當前月份往後推幾個月，必須大於 0
            
        Returns:
            List[Dict]: 節假日資料列表，每個字典包含：
                - holiday_name (str): 節假日名稱
                - holiday_date (str): 節假日日期 (YYYY-MM-DD)
                - departure_date (str): 建議的出發日期 (YYYY-MM-DD)
                - return_date (str): 建議的回程日期 (YYYY-MM-DD)
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
    
    def _call_api(
        self, 
        api_url: str, 
        payload: Dict, 
        timeout: int,
        error_message: str
    ) -> Dict:
        """
        呼叫節日日期計算 API
        
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
            print(f"HolidayCalculationService API 請求失敗: {e}")
            raise
