# -*- coding: utf-8 -*-
"""
Photo Viewer Widget - 表示専用ウィジェット

編集済み画像を表示するための読み取り専用ウィジェット
"""

import os
from qgis.gui import QgsEditorWidgetWrapper
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsView, 
    QGraphicsScene, QGraphicsPixmapItem
)
from qgis.PyQt.QtGui import QPixmap, QImage, QPainter
from qgis.PyQt.QtCore import Qt, QRectF, QTimer
from qgis.core import QgsMessageLog, Qgis


class PhotoViewerWidget(QgsEditorWidgetWrapper):
    """
    写真表示専用ウィジェット（編集不可）
    """
    
    def __init__(self, vl, fieldIdx, editor, parent):
        super().__init__(vl, fieldIdx, editor, parent)
        self.widget = None
        self.graphics_view = None
        self.graphics_scene = None
        self.pixmap_item = None
        self.status_label = None
        self._current_feature = None
    
    def createWidget(self, parent):
        """ウィジェット作成"""
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # ステータス表示
        self.status_label = QLabel("編集済み画像", widget)
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # QGraphicsView（画像表示エリア）- 読み取り専用
        self.graphics_scene = QGraphicsScene(widget)
        self.graphics_view = QGraphicsView(self.graphics_scene, widget)
        self.graphics_view.setMinimumSize(300, 200)
        self.graphics_view.setMaximumSize(600, 400)
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #ccc;
                background-color: #f8f8f8;
            }
        """)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # インタラクションを無効化
        self.graphics_view.setInteractive(False)
        
        layout.addWidget(self.graphics_view)
        
        self.widget = widget
        return widget
    
    def initWidget(self, editor):
        """初期化"""
        pass
    
    def setFeature(self, feature):
        """地物がセットされた時"""
        super().setFeature(feature)
        self._current_feature = feature
        self.load_photo()
    
    def value(self):
        return None
    
    def valid(self):
        return True
    
    def _fit_to_view(self):
        """画像をビューにフィット"""
        if self.pixmap_item and self.graphics_scene:
            self.graphics_view.fitInView(
                self.graphics_scene.sceneRect(),
                Qt.KeepAspectRatio
            )
    
    def load_photo(self):
        """写真読み込み"""
        try:
            # 地物取得
            feature = None
            try:
                feature = self.formFeature()
            except AttributeError:
                if hasattr(self, '_current_feature'):
                    feature = self._current_feature
            except:
                pass
            
            if not feature or not feature.isValid():
                self.status_label.setText("編集済み画像: なし")
                self.status_label.setStyleSheet("color: #999;")
                self.graphics_scene.clear()
                return
            
            # photo_edited_pathを取得
            field_names = feature.fields().names()
            photo_path = None
            
            for field_name in ['photo_edited_path', 'photo_edited']:
                if field_name in field_names:
                    path = feature[field_name]
                    if path and str(path).strip() and str(path).strip().upper() != 'NULL':
                        photo_path = str(path).strip()
                        break
            
            if not photo_path:
                self.status_label.setText("編集済み画像: 未保存")
                self.status_label.setStyleSheet("color: #999;")
                self.graphics_scene.clear()
                return
            
            if not os.path.exists(photo_path):
                self.status_label.setText(f"❌ ファイルなし")
                self.status_label.setStyleSheet("color: #FF3B30;")
                self.graphics_scene.clear()
                return
            
            # 画像読み込み
            pixmap = self._load_image_as_pixmap(photo_path)
            
            if pixmap is None or pixmap.isNull():
                self.status_label.setText("❌ 読み込み失敗")
                self.status_label.setStyleSheet("color: #FF3B30;")
                return
            
            # シーンをクリアして画像を追加
            self.graphics_scene.clear()
            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.graphics_scene.addItem(self.pixmap_item)
            
            # シーン範囲設定
            rect = pixmap.rect()
            self.graphics_scene.setSceneRect(QRectF(rect.x(), rect.y(), rect.width(), rect.height()))
            
            # フィット
            QTimer.singleShot(100, lambda: self._fit_to_view())
            
            self.status_label.setText(f"✓ {os.path.basename(photo_path)}")
            self.status_label.setStyleSheet("color: #34C759;")
            
        except Exception as e:
            self.status_label.setText(f"❌ エラー")
            self.status_label.setStyleSheet("color: #FF3B30;")
            QgsMessageLog.logMessage(
                f"PhotoViewer エラー: {str(e)}",
                "PhotoEditor", Qgis.Warning
            )
    
    def _load_image_as_pixmap(self, photo_path):
        """画像をQPixmapとして読み込む"""
        try:
            qimage = QImage(photo_path)
            if not qimage.isNull():
                qimage = qimage.convertToFormat(QImage.Format_RGB32)
                return QPixmap.fromImage(qimage)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"画像読み込み失敗: {str(e)}",
                "PhotoEditor", Qgis.Warning
            )
        return None
