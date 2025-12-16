# -*- coding: utf-8 -*-
"""
写真ファイル名パーサー

ファイル名形式: [ビルコード-設備名_設備番号].jpg
例: BLD001-橋梁主桁_01.jpg
"""

import re
from typing import Optional, Dict
from qgis.core import QgsMessageLog, Qgis


class PhotoFileNameParser:
    """
    写真ファイル名のパーサー
    
    ファイル名形式: [ビルコード-設備名_設備番号].jpg
    """
    
    # ファイル名パターン（正規表現）
    FILENAME_PATTERN = re.compile(
        r'^(?P<build_code>[^-]+)-'           # ビルコード（ハイフンまで）
        r'(?P<facility_name>[^_]+)_'         # 設備名（アンダースコアまで）
        r'(?P<facility_number>[^.]+)'        # 設備番号（拡張子まで）
        r'(?P<extension>\.[^.]+)$'           # 拡張子
    )
    
    @classmethod
    def parse(cls, filename: str) -> Optional[Dict[str, str]]:
        """
        ファイル名を解析
        
        Args:
            filename: ファイル名（拡張子含む）
            
        Returns:
            Dict: 解析結果
                - build_code: ビルコード
                - facility_name: 設備名
                - facility_number: 設備番号
                - extension: 拡張子
            None: 解析失敗時
        """
        try:
            match = cls.FILENAME_PATTERN.match(filename)
            if match:
                return match.groupdict()
            return None
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ファイル名解析エラー: {e}",
                "PhotoEditor",
                Qgis.Critical
            )
            return None
    
    @classmethod
    def build(cls, build_code: str, facility_name: str, 
              facility_number: str, extension: str = '.jpg') -> str:
        """
        ファイル名を生成
        
        Args:
            build_code: ビルコード
            facility_name: 設備名（日本語）
            facility_number: 設備番号
            extension: 拡張子（デフォルト: .jpg）
            
        Returns:
            str: ファイル名
        """
        try:
            # ファイル名を構築
            filename = f"{build_code}-{facility_name}_{facility_number}{extension}"
            
            return filename
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ファイル名生成エラー: {e}",
                "PhotoEditor",
                Qgis.Critical
            )
            return None
    
    @classmethod
    def build_unique_key(cls, build_code: str, facility_name: str, 
                         facility_number: str) -> str:
        """
        ユニーク設備KEYを生成
        
        Args:
            build_code: ビルコード
            facility_name: 設備名
            facility_number: 設備番号
            
        Returns:
            str: ユニーク設備KEY
        """
        try:
            unique_key = f"{build_code}{facility_name}_{facility_number}"
            return unique_key
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ユニークKEY生成エラー: {e}",
                "PhotoEditor",
                Qgis.Critical
            )
            return None
