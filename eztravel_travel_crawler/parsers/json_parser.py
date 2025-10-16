"""
JSON解析器模組

此模組提供了一個專門用於解析易遊網 REST API 返回的 JSON 數據的解析器類別。
該類別負責從原始 API 響應中提取和結構化機票資料。

主要功能：
- 解析 API 返回的 JSON 響應數據
- 提取航班基本信息，如航班編號、日期、價格等
- 提取航段資料，包括去程和回程
- 提取票價和稅金信息
- 將提取的數據轉換為結構化的內部數據模型
- 支持將去程和回程數據進行組合匹配

依賴項：
- dataclasses: 用於創建數據類
- typing: 用於類型提示
- json: 用於處理 JSON 數據
- pandas: 用於將數據轉換為 DataFrame 進行調試
"""

import traceback
import re
import datetime
from typing import Dict, List, Any, Optional
from models.flight_info import FlightInfo
from models.flight_segment import FlightSegment
from utils.log_manager import LogManager
from config.config_manager import ConfigManager

class JsonParser:
    """
    JSON解析器類別
    
    負責解析從易遊網 REST API 獲取的 JSON 數據，
    提取去程航班信息，並能將回程數據與去程數據結合，處理一對多的關係。
    
    屬性：
        log_manager (LogManager): 日誌管理器實例
        config_manager (ConfigManager): 配置管理器實例
        api_response (Dict[str, Any]): API 返回的原始 JSON 數據
        structured_data (List[FlightInfo]): 結構化後的航班數據列表 (通常是去程航班)
    """

    def __init__(self, log_manager: LogManager, config_manager: ConfigManager):
        """
        初始化 JSON 解析器
        
        參數：
            log_manager (LogManager): 日誌管理器實例
            config_manager (ConfigManager): 配置管理器實例
        """

        self.log_manager = log_manager
        self.config_manager = config_manager
        self.api_response: Any = None
        self.structured_data: List[FlightInfo] = []

    def parse_api_response(self, json_data: Dict[str, Any]) -> bool:
        """
        解析 API 返回的 JSON 數據 (主要用於去程)
        
        參數：
            json_data (Dict[str, Any]): API 返回的 JSON 數據
            
        返回：
            bool: 解析是否成功
        """

        try:
            self.api_response = json_data
            self.structured_data = []
            data = json_data.get('data')
            if not isinstance(data, list):
                self.log_manager.log_error("去程 API 響應無效：缺少 'data' 或格式非 list")
                return False
            for idx, item in enumerate(data):
                try:
                    flight = self.extract_outbound_flight_data(item)
                    if flight:
                        self.structured_data.append(flight)
                    else:
                        self.log_manager.log_warning(f"第 {idx+1} 筆去程資料提取失敗，已跳過")
                except Exception:
                    self.log_manager.log_error(f"第 {idx+1} 筆去程資料例外：\n{traceback.format_exc()}")
            self.log_manager.log_debug(f"成功解析 {len(self.structured_data)}/{len(data)} 筆去程航班")
            return True
        except Exception:
            self.log_manager.log_error(f"解析去程 API 未預期錯誤：\n{traceback.format_exc()}")
            return False

    def parse_inbound_response(self, json_data: Dict[str, Any], outbound_flight_info: FlightInfo) -> List[FlightInfo]:
        """
        解析回程 API 響應並與提供的去程信息結合，生成完整的航班資訊列表。
        處理一個去程對應多程的情況。

        參數：
            json_data (Dict[str, Any]): 回程 API 返回的 JSON 數據
            outbound_flight_info (FlightInfo): 對應的去程航班資訊
        返回：
            List[FlightInfo]: 包含完整去回程資訊的航班列表 (每個元素是一個去回程組合)
        """
        complete: List[FlightInfo] = []
        
        try:
            data = json_data.get('data')
            if not isinstance(data, list):
                self.log_manager.log_error("回程 API 響應無效：缺少 'data' 或格式非 list")
                return complete
            for idx, item in enumerate(data):
                try:
                    basic = self._extract_flight_info(item)
                    sectors = item.get('sectors', [])
                    segments = self._extract_segment_data(sectors)
                    if not segments:
                        self.log_manager.log_warning(f"回程第 {idx+1} 筆航段解析失敗")
                        continue
                    fare = self._extract_fare_info(item)
                    return_date = basic.get('departure_date', '')
                    if not return_date:
                        self.log_manager.log_warning(f"回程第 {idx+1} 筆日期解析失敗")
                        continue
                    flight = FlightInfo(
                        departure_date=outbound_flight_info.departure_date,
                        return_date=return_date,
                        price=fare.get('total_price', 0.0),
                        tax=fare.get('total_tax', 0.0),
                        outbound_segments=outbound_flight_info.outbound_segments,
                        inbound_segments=segments,
                        routeSearchToken=outbound_flight_info.routeSearchToken,
                        outboundToken=outbound_flight_info.outboundToken,
                        product_desc=outbound_flight_info.product_desc
                    )
                    complete.append(flight)
    
                except Exception:
                    self.log_manager.log_error(f"處理第 {idx+1} 筆回程例外：\n{traceback.format_exc()}")
            self.log_manager.log_debug(f"為 routeSearchToken {outbound_flight_info.routeSearchToken} 生成 {len(complete)} 組合")
            
        except Exception:
            self.log_manager.log_error(f"解析回程 API 未預期錯誤：\n{traceback.format_exc()}")
        return complete

    def extract_outbound_flight_data(self, flight_item: Dict[str, Any]) -> Optional[FlightInfo]:
        '''
        從航班項目數據中提取去程航班信息，包括 routeSearchToken 和 outboundToken

        參數：
            flight_item (Dict[str, Any]): 包含單個去程航班信息的字典
        返回：
            Optional[FlightInfo]: 結構化的去程航班信息對象，如果提取失敗則返回 None
        '''
        try:
            basic = self._extract_flight_info(flight_item)
            sectors = flight_item.get('sectors', [])
            segments = self._extract_segment_data(sectors)
            if not segments:
                return None
            fare = self._extract_fare_info(flight_item)
            route_search_token = flight_item.get('seats')[0].get('routeSearchToken')
            outbound_token = flight_item.get('seats')[0].get('outboundToken')
            
            # 提取 product_desc
            product_desc = self._extract_product_desc(flight_item)

            if not route_search_token or not outbound_token:
                self.log_manager.log_warning("缺少 routeSearchToken 或 outboundToken，無法查回程")
                return None
            
            flight_info_to_return = FlightInfo(
                departure_date=basic.get('departure_date'),
                return_date=None,
                price=fare.get('total_price', 0.0),
                tax=fare.get('total_tax', 0.0),
                outbound_segments=segments,
                inbound_segments=[],
                routeSearchToken=route_search_token,
                outboundToken=outbound_token,
                product_desc=product_desc
            )
            
            return flight_info_to_return
        except Exception as e:
            self.log_manager.log_error(f"extract_outbound_flight_data 錯誤：{e}")
            return None
        

    def get_structured_data(self) -> List[FlightInfo]:
        """
        取得 parse_api_response 後的去程航班列表

        返回：
            List[FlightInfo]: 包含去程航班信息的列表
        """
        return self.structured_data

    def _extract_flight_info(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        從航班項目數據中提取去程航班信息，包括 departure_airport, arrival_airport, departure_date, departure_time, arrival_date, arrival_time

        參數：
            flight_data (Dict[str, Any]): 包含單個去程航班信息的字典
        返回：
            Dict[str, Any]: 包含航班信息的字典
        """
        info: Dict[str, Any] = {}
        info['departure_airport'] = flight_data.get('departureAirportCode', '')
        info['arrival_airport']   = flight_data.get('arrivalAirportCode', '')
        info['departure_date']    = self._parse_date(
            flight_data.get('departureDate', ''),
            current_year=datetime.datetime.now().year
        )
        info['departure_time']    = flight_data.get('departureTime', '')
        info['arrival_date']      = self._parse_date(
            flight_data.get('arrivalDate', ''),
            current_year=datetime.datetime.now().year
        )
        info['arrival_time']      = flight_data.get('arrivalTime', '')
        return info

    def _extract_fare_info(self, flight_item: Dict[str, Any]) -> Dict[str, float]:
        """
        根據 seats 欄位提取票價和稅金

        參數：
            flight_item (Dict[str, Any]): 包含單個去程航班信息的字典
        返回：
            Dict[str, float]: 包含票價和稅金的字典
        """
        fare_data: Dict[str, float] = {'total_price': 0.0, 'total_tax': 0.0}
        seats = flight_item.get('seats') or []
        if seats:
            seat = seats[0]
            try:
                # 優先使用含稅價格，如果不存在則退回到 price
                total_price = float(seat.get('adultPrice', seat.get('priceWithoutTax', 0)))
                total_tax = float(seat.get('adultTax', 0))
                fare_data['total_price'] = total_price
                fare_data['total_tax']   = total_tax
            except (ValueError, TypeError):
                self.log_manager.log_warning("票價或稅金格式錯誤，使用預設值")
        else:
            self.log_manager.log_warning("未找到價格資訊 (seats 欄位) , 使用預設價格")
        return fare_data
    
    def _extract_product_desc(self, flight_item: Dict[str, Any]) -> bool:
        """
        根據 seats 欄位提取是否為海外供應商的布林值

        參數：
            flight_item (Dict[str, Any]): 包含單個航班信息的字典
        返回：
            bool: 是否為海外供應商
        """
        seats = flight_item.get('seats')
        if seats and isinstance(seats, list) and len(seats) > 0:
            product_desc_str = seats[0].get('productDesc', '')
            return product_desc_str == '由海外供應商提供'
        return False

    def _extract_segment_data(self, sectors: List[Dict[str, Any]]) -> List[FlightSegment]:
        """
        從航班項目數據中提取航段資料，包括 airlineCode, flightNo, cabinClassList

        參數：
            sectors (List[Dict[str, Any]]): 包含航段資料的列表
        返回：
            List[FlightSegment]: 包含航段資料的列表 
        """
        segments: List[FlightSegment] = []
        for i, sec in enumerate(sectors):
            try:
                airline = sec.get('airlineCode', '') 
                no = sec.get('flightNo', '')

                if not no: # 如果 flightNo 為空，則跳過
                    self.log_manager.log_warning(f"第 {i+1} 航段缺少 flightNo")
                    continue

                # 移除 flightNo 中可能存在的多餘空格，以提高比較的可靠性
                no_cleaned = no.strip()
                airline_cleaned = airline.strip()

                flight_no_final = ""
                if airline_cleaned and no_cleaned.upper().startswith(airline_cleaned.upper()):
                    # 如果 flightNo (no_cleaned) 已經以 airlineCode (airline_cleaned) 開頭 (忽略大小寫比較)
                    # 則直接使用 flightNo (no_cleaned) 作為最終的航班號
                    flight_no_final = no_cleaned 
                elif airline_cleaned and no_cleaned:
                    # 否則，如果兩者都存在，則拼接它們
                    flight_no_final = f"{airline_cleaned}{no_cleaned}"
                elif no_cleaned:
                    # 如果只有 flightNo (no_cleaned) 存在，則使用它
                    flight_no_final = no_cleaned
                else:
                    # 理論上不應該執行到這裡，因為前面有 if not no: continue
                    self.log_manager.log_warning(f"第 {i+1} 航段無法確定航班編號 (airline: '{airline}', no: '{no}')")
                    continue
                
                cabin = (sec.get('cabinDesc', "") + sec.get('bookingClass', "")).strip() or ""
                segments.append(FlightSegment(flight_number=flight_no_final.upper(), cabin_class=cabin))
            except Exception as e:
                self.log_manager.log_error(f"第 {i+1} 航段解析失敗：{e}")
        return segments

    def _parse_date(self, date_str: str, current_year: Optional[int] = None) -> Optional[datetime.date]:
        """
        解析日期字串，返回 datetime.date 對象

        參數：
            date_str (str): 日期字串
            current_year (Optional[int]): 當前年份
        返回：
            Optional[datetime.date]: 解析後的日期對象，如果解析失敗則返回 None
        """
        if not isinstance(date_str, str) or not date_str:
            self.log_manager.log_warning(f"日期無效: '{date_str}'")
            return None
        try:
            # YYYY-MM-DD
            if '-' in date_str:
                parts = date_str.split('-')
                if len(parts)==3 and all(p.isdigit() for p in parts):
                    y,m,d = map(int, parts)
                    return datetime.date(y,m,d)
                return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            # M月D日
            if '月' in date_str and '日' in date_str and current_year:
                m = int(re.search(r"(\d{1,2})月", date_str).group(1))
                d = int(re.search(r"月(\d{1,2})日", date_str).group(1))
                return datetime.date(current_year, m, d)
            # YYYYMMDD
            if len(date_str)==8 and date_str.isdigit():
                return datetime.datetime.strptime(date_str, '%Y%m%d').date()
            self.log_manager.log_warning(f"未知日期格式: '{date_str}'")
        except Exception as e:
            self.log_manager.log_error(f"解析日期 '{date_str}' 錯誤: {e}")
        return None

