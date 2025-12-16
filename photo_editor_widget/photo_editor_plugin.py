# -*- coding: utf-8 -*-
"""
Photo Editor Widget Plugin

設備点検用写真編集プラグイン
"""

from qgis.gui import QgsGui
from qgis.core import QgsMessageLog, Qgis


class PhotoEditorPlugin:
    """
    Photo Editor Widget プラグインメイン
    """
    
    def __init__(self, iface):
        self.iface = iface
        self.editor_factory = None
        self.viewer_factory = None
    
    def initGui(self):
        """プラグイン起動時の初期化"""
        try:
            from .photo_editor_factory import PhotoEditorWidgetFactory, PhotoViewerWidgetFactory
            
            registry = QgsGui.editorWidgetRegistry()
            
            # Photo Editor（編集用）を登録
            self.editor_factory = PhotoEditorWidgetFactory("Photo Editor")
            registry.registerWidget("Photo Editor", self.editor_factory)
            
            # Photo Viewer（表示専用）を登録
            self.viewer_factory = PhotoViewerWidgetFactory("Photo Viewer")
            registry.registerWidget("Photo Viewer", self.viewer_factory)
            
            QgsMessageLog.logMessage(
                "✓ Photo Editor / Photo Viewer ウィジェットを登録しました",
                "PhotoEditor",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"❌ プラグイン初期化エラー: {str(e)}",
                "PhotoEditor",
                Qgis.Critical
            )
    
    def unload(self):
        """プラグイン終了時のクリーンアップ"""
        try:
            QgsMessageLog.logMessage(
                "✓ Photo Editor プラグインを終了しました",
                "PhotoEditor",
                Qgis.Info
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"❌ プラグイン終了エラー: {str(e)}",
                "PhotoEditor",
                Qgis.Critical
            )
