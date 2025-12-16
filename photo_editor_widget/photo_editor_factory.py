# -*- coding: utf-8 -*-
"""
Photo Editor Widget Factory

QGISエディタウィジェットのファクトリクラス
"""

from qgis.gui import QgsEditorWidgetFactory, QgsEditorConfigWidget
from qgis.PyQt.QtWidgets import QWidget


class PhotoEditorConfigWidget(QgsEditorConfigWidget):
    """設定ウィジェット（空実装）"""
    
    def __init__(self, vl, fieldIdx, parent):
        super().__init__(vl, fieldIdx, parent)
    
    def config(self):
        """設定を返す"""
        return {}
    
    def setConfig(self, config):
        """設定を受け取る"""
        pass


class PhotoEditorWidgetFactory(QgsEditorWidgetFactory):
    """
    写真編集ウィジェットファクトリ
    """
    
    def __init__(self, name):
        super().__init__(name)
    
    def create(self, vl, fieldIdx, editor, parent):
        """ウィジェットインスタンスを作成"""
        from .photo_editor_widget import PhotoEditorWidget
        return PhotoEditorWidget(vl, fieldIdx, editor, parent)
    
    def configWidget(self, vl, fieldIdx, parent):
        """設定ウィジェットを返す"""
        return PhotoEditorConfigWidget(vl, fieldIdx, parent)


class PhotoViewerWidgetFactory(QgsEditorWidgetFactory):
    """
    写真表示専用ウィジェットファクトリ（編集不可）
    """
    
    def __init__(self, name):
        super().__init__(name)
    
    def create(self, vl, fieldIdx, editor, parent):
        """ウィジェットインスタンスを作成"""
        from .photo_viewer_widget import PhotoViewerWidget
        return PhotoViewerWidget(vl, fieldIdx, editor, parent)
    
    def configWidget(self, vl, fieldIdx, parent):
        """設定ウィジェットを返す"""
        return PhotoEditorConfigWidget(vl, fieldIdx, parent)
