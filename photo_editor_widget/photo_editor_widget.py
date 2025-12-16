# -*- coding: utf-8 -*-
"""
Photo Editor Widget - メインウィジェット

QGISカスタムウィジェットとして写真の表示・編集を行う
QGraphicsViewベースの実装
"""

import os
from datetime import datetime
from pathlib import Path
from qgis.gui import QgsEditorWidgetWrapper
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsPolygonItem,
    QToolButton, QButtonGroup, QColorDialog, QSpinBox,
    QFrame, QSizePolicy
)
from qgis.PyQt.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QBrush,
    QPainterPath, QPolygonF, QFont
)
from qgis.PyQt.QtCore import Qt, QPointF, QRectF, QLineF, QTimer
from qgis.core import QgsMessageLog, Qgis

from .utils.file_parser import PhotoFileNameParser


class DrawingTool:
    """描画ツールの定数"""
    SELECT = 'select'
    PEN = 'pen'
    LINE = 'line'
    ARROW = 'arrow'
    RECT = 'rect'
    ELLIPSE = 'ellipse'
    TEXT = 'text'


class PhotoGraphicsView(QGraphicsView):
    """
    カスタムGraphicsView - マウスイベントを処理して描画を行う
    """
    
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.editor_widget = None  # 親ウィジェットへの参照
        self.drawing = False
        self.start_point = None
        self.current_item = None
        self.pen_path = None
        
    def set_editor_widget(self, editor_widget):
        """親ウィジェットへの参照を設定"""
        self.editor_widget = editor_widget
    
    def mousePressEvent(self, event):
        """マウス押下"""
        if not self.editor_widget:
            super().mousePressEvent(event)
            return
        
        tool = self.editor_widget.current_tool
        
        if tool == DrawingTool.SELECT:
            super().mousePressEvent(event)
            return
        
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = self.mapToScene(event.pos())
            
            if tool == DrawingTool.PEN:
                self._start_pen_drawing()
            elif tool == DrawingTool.TEXT:
                self._add_text()
                self.drawing = False
    
    def mouseMoveEvent(self, event):
        """マウス移動"""
        if not self.editor_widget:
            super().mouseMoveEvent(event)
            return
        
        tool = self.editor_widget.current_tool
        
        if tool == DrawingTool.SELECT:
            super().mouseMoveEvent(event)
            return
        
        if self.drawing and self.start_point:
            current_point = self.mapToScene(event.pos())
            
            if tool == DrawingTool.PEN:
                self._continue_pen_drawing(current_point)
            elif tool in [DrawingTool.LINE, DrawingTool.ARROW, DrawingTool.RECT, DrawingTool.ELLIPSE]:
                self._update_shape_preview(current_point)
    
    def mouseReleaseEvent(self, event):
        """マウスリリース"""
        if not self.editor_widget:
            super().mouseReleaseEvent(event)
            return
        
        tool = self.editor_widget.current_tool
        
        if tool == DrawingTool.SELECT:
            super().mouseReleaseEvent(event)
            return
        
        if self.drawing and event.button() == Qt.LeftButton:
            end_point = self.mapToScene(event.pos())
            
            if tool == DrawingTool.PEN:
                self._finish_pen_drawing()
            elif tool == DrawingTool.LINE:
                self._create_line(end_point)
            elif tool == DrawingTool.ARROW:
                self._create_arrow(end_point)
            elif tool == DrawingTool.RECT:
                self._create_rect(end_point)
            elif tool == DrawingTool.ELLIPSE:
                self._create_ellipse(end_point)
            
            self.drawing = False
            self.start_point = None
            self.current_item = None
    
    def _get_pen(self):
        """現在の描画ペンを取得"""
        pen = QPen(self.editor_widget.current_color)
        pen.setWidth(self.editor_widget.line_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen
    
    def _start_pen_drawing(self):
        """ペン描画開始"""
        self.pen_path = QPainterPath()
        self.pen_path.moveTo(self.start_point)
        self.current_item = QGraphicsPathItem(self.pen_path)
        self.current_item.setPen(self._get_pen())
        self.scene().addItem(self.current_item)
    
    def _continue_pen_drawing(self, point):
        """ペン描画継続"""
        if self.pen_path and self.current_item:
            self.pen_path.lineTo(point)
            self.current_item.setPath(self.pen_path)
    
    def _finish_pen_drawing(self):
        """ペン描画終了"""
        self.pen_path = None
    
    def _update_shape_preview(self, current_point):
        """図形プレビュー更新"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        tool = self.editor_widget.current_tool
        pen = self._get_pen()
        
        if tool == DrawingTool.LINE:
            self.current_item = QGraphicsLineItem(
                QLineF(self.start_point, current_point)
            )
            self.current_item.setPen(pen)
        
        elif tool == DrawingTool.ARROW:
            # 矢印は線として表示（プレビュー）
            self.current_item = QGraphicsLineItem(
                QLineF(self.start_point, current_point)
            )
            self.current_item.setPen(pen)
        
        elif tool == DrawingTool.RECT:
            rect = QRectF(self.start_point, current_point).normalized()
            self.current_item = QGraphicsRectItem(rect)
            self.current_item.setPen(pen)
            self.current_item.setBrush(QBrush(Qt.transparent))
        
        elif tool == DrawingTool.ELLIPSE:
            rect = QRectF(self.start_point, current_point).normalized()
            self.current_item = QGraphicsEllipseItem(rect)
            self.current_item.setPen(pen)
            self.current_item.setBrush(QBrush(Qt.transparent))
        
        if self.current_item:
            self.scene().addItem(self.current_item)
    
    def _create_line(self, end_point):
        """直線作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        line = QGraphicsLineItem(QLineF(self.start_point, end_point))
        line.setPen(self._get_pen())
        line.setFlag(QGraphicsLineItem.ItemIsSelectable, True)
        line.setFlag(QGraphicsLineItem.ItemIsMovable, True)
        self.scene().addItem(line)
        
        QgsMessageLog.logMessage(
            f"直線作成: ({self.start_point.x():.0f},{self.start_point.y():.0f}) → ({end_point.x():.0f},{end_point.y():.0f})",
            "PhotoEditor", Qgis.Info
        )
    
    def _create_arrow(self, end_point):
        """矢印作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        pen = self._get_pen()
        
        # 矢印の本体（線）
        line = QGraphicsLineItem(QLineF(self.start_point, end_point))
        line.setPen(pen)
        line.setFlag(QGraphicsLineItem.ItemIsSelectable, True)
        line.setFlag(QGraphicsLineItem.ItemIsMovable, True)
        self.scene().addItem(line)
        
        # 矢印の先端（三角形）
        arrow_size = self.editor_widget.line_width * 4
        
        # 方向ベクトル
        dx = end_point.x() - self.start_point.x()
        dy = end_point.y() - self.start_point.y()
        length = (dx**2 + dy**2)**0.5
        
        if length > 0:
            # 正規化
            dx /= length
            dy /= length
            
            # 矢印の先端の三角形の点
            p1 = end_point
            p2 = QPointF(
                end_point.x() - arrow_size * dx + arrow_size * 0.5 * dy,
                end_point.y() - arrow_size * dy - arrow_size * 0.5 * dx
            )
            p3 = QPointF(
                end_point.x() - arrow_size * dx - arrow_size * 0.5 * dy,
                end_point.y() - arrow_size * dy + arrow_size * 0.5 * dx
            )
            
            arrow_head = QPolygonF([p1, p2, p3])
            arrow_item = QGraphicsPolygonItem(arrow_head)
            arrow_item.setPen(pen)
            arrow_item.setBrush(QBrush(self.editor_widget.current_color))
            arrow_item.setFlag(QGraphicsPolygonItem.ItemIsSelectable, True)
            arrow_item.setFlag(QGraphicsPolygonItem.ItemIsMovable, True)
            self.scene().addItem(arrow_item)
        
        QgsMessageLog.logMessage(
            f"矢印作成: ({self.start_point.x():.0f},{self.start_point.y():.0f}) → ({end_point.x():.0f},{end_point.y():.0f})",
            "PhotoEditor", Qgis.Info
        )
    
    def _create_rect(self, end_point):
        """四角形作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        rect = QRectF(self.start_point, end_point).normalized()
        rect_item = QGraphicsRectItem(rect)
        rect_item.setPen(self._get_pen())
        rect_item.setBrush(QBrush(Qt.transparent))
        rect_item.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        rect_item.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.scene().addItem(rect_item)
        
        QgsMessageLog.logMessage(
            f"四角形作成: {rect.width():.0f}x{rect.height():.0f}",
            "PhotoEditor", Qgis.Info
        )
    
    def _create_ellipse(self, end_point):
        """楕円作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        rect = QRectF(self.start_point, end_point).normalized()
        ellipse_item = QGraphicsEllipseItem(rect)
        ellipse_item.setPen(self._get_pen())
        ellipse_item.setBrush(QBrush(Qt.transparent))
        ellipse_item.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        ellipse_item.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.scene().addItem(ellipse_item)
        
        QgsMessageLog.logMessage(
            f"楕円作成: {rect.width():.0f}x{rect.height():.0f}",
            "PhotoEditor", Qgis.Info
        )
    
    def _add_text(self):
        """テキスト追加"""
        text_item = QGraphicsTextItem("テキスト")
        text_item.setPos(self.start_point)
        text_item.setDefaultTextColor(self.editor_widget.current_color)
        font = QFont()
        font.setPointSize(self.editor_widget.line_width * 4)
        text_item.setFont(font)
        text_item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        text_item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.scene().addItem(text_item)
        
        QgsMessageLog.logMessage(
            f"テキスト追加: ({self.start_point.x():.0f},{self.start_point.y():.0f})",
            "PhotoEditor", Qgis.Info
        )


class PhotoEditorWidget(QgsEditorWidgetWrapper):
    """
    写真編集カスタムウィジェット
    """
    
    def __init__(self, vl, fieldIdx, editor, parent):
        super().__init__(vl, fieldIdx, editor, parent)
        self.widget = None
        self.graphics_view = None
        self.graphics_scene = None
        self.pixmap_item = None
        self.status_label = None
        self.current_photo_path = None
        self._current_feature = None
        
        # 描画設定
        self.current_tool = DrawingTool.SELECT
        self.current_color = QColor('#FF0000')
        self.line_width = 3
        
        # ツールボタン
        self.tool_buttons = {}
    
    def createWidget(self, parent):
        """ウィジェット作成"""
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # ステータス表示
        self.status_label = QLabel("準備中...", widget)
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # ツールバー
        toolbar = self._create_toolbar(widget)
        layout.addWidget(toolbar)
        
        # QGraphicsView（画像表示エリア）
        self.graphics_scene = QGraphicsScene(widget)
        self.graphics_view = PhotoGraphicsView(self.graphics_scene, widget)
        self.graphics_view.set_editor_widget(self)
        self.graphics_view.setMinimumSize(600, 400)
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #ccc;
                background-color: #f0f0f0;
            }
        """)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.graphics_view)
        
        # 下部ボタンエリア
        bottom_layout = QHBoxLayout()
        
        # 削除ボタン
        self.delete_btn = QPushButton("🗑 削除", widget)
        self.delete_btn.setStyleSheet(self._button_style("#FF9500"))
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        bottom_layout.addWidget(self.delete_btn)
        
        # 全削除ボタン
        self.clear_btn = QPushButton("🧹 全削除", widget)
        self.clear_btn.setStyleSheet(self._button_style("#FF3B30"))
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        bottom_layout.addWidget(self.clear_btn)
        
        bottom_layout.addStretch()
        
        # 保存ボタン
        self.save_btn = QPushButton("💾 保存", widget)
        self.save_btn.setStyleSheet(self._button_style("#34C759"))
        self.save_btn.clicked.connect(self._on_save_clicked)
        bottom_layout.addWidget(self.save_btn)
        
        layout.addLayout(bottom_layout)
        
        self.widget = widget
        QgsMessageLog.logMessage(
            f"createWidget完了: delete_btn={self.delete_btn}, save_btn={self.save_btn}, tool_buttons={list(self.tool_buttons.keys())}",
            "PhotoEditor", Qgis.Info
        )
        return widget
    
    def _button_style(self, color):
        """ボタンスタイルを生成"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {color}CC;
            }}
        """
    
    def _create_toolbar(self, parent):
        """ツールバー作成"""
        toolbar = QFrame(parent)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # ツールボタングループ
        self.button_group = QButtonGroup(parent)
        self.button_group.setExclusive(True)
        
        tools = [
            (DrawingTool.SELECT, "👆", "選択"),
            (DrawingTool.PEN, "✏️", "ペン"),
            (DrawingTool.LINE, "📏", "直線"),
            (DrawingTool.ARROW, "➡️", "矢印"),
            (DrawingTool.RECT, "⬜", "四角"),
            (DrawingTool.ELLIPSE, "⭕", "楕円"),
            (DrawingTool.TEXT, "🔤", "テキスト"),
        ]
        
        for tool_id, icon, tooltip in tools:
            btn = QToolButton(parent)
            btn.setText(icon)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setMinimumSize(32, 32)
            btn.setStyleSheet("""
                QToolButton {
                    font-size: 16px;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    padding: 4px;
                }
                QToolButton:checked {
                    background-color: #007AFF;
                    border-color: #0051D5;
                }
                QToolButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            self.button_group.addButton(btn)
            self.tool_buttons[tool_id] = btn
            layout.addWidget(btn)
            QgsMessageLog.logMessage(f"ツールボタン作成: {tool_id}", "PhotoEditor", Qgis.Info)
        
        # ボタングループのシグナル接続
        self.button_group.buttonClicked.connect(self._on_tool_button_clicked)
        
        # デフォルトで選択ツールをチェック
        self.tool_buttons[DrawingTool.SELECT].setChecked(True)
        
        # セパレータ
        sep = QFrame(parent)
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #ccc;")
        layout.addWidget(sep)
        
        # 色選択ボタン
        self.color_btn = QPushButton("", parent)
        self.color_btn.setMinimumSize(32, 32)
        self.color_btn.setMaximumSize(32, 32)
        self.color_btn.setToolTip("色選択")
        self._update_color_button()
        self.color_btn.clicked.connect(self._on_color_clicked)
        layout.addWidget(self.color_btn)
        
        # 線幅スピンボックス
        self.width_spin = QSpinBox(parent)
        self.width_spin.setRange(1, 20)
        self.width_spin.setValue(self.line_width)
        self.width_spin.setToolTip("線の太さ")
        self.width_spin.setMinimumWidth(50)
        self.width_spin.valueChanged.connect(self._set_line_width)
        layout.addWidget(self.width_spin)
        
        layout.addStretch()
        
        # フィットボタン
        self.fit_btn = QPushButton("🔍", parent)
        self.fit_btn.setToolTip("画面にフィット")
        self.fit_btn.setMinimumSize(32, 32)
        self.fit_btn.setMaximumSize(32, 32)
        self.fit_btn.clicked.connect(self._on_fit_clicked)
        layout.addWidget(self.fit_btn)
        
        return toolbar
    
    def _on_delete_clicked(self):
        """削除ボタンクリック"""
        QgsMessageLog.logMessage("🗑 削除ボタンクリック", "PhotoEditor", Qgis.Info)
        self._delete_selected()
    
    def _on_clear_clicked(self):
        """全削除ボタンクリック"""
        QgsMessageLog.logMessage("🧹 全削除ボタンクリック", "PhotoEditor", Qgis.Info)
        self._clear_drawings()
    
    def _on_save_clicked(self):
        """保存ボタンクリック"""
        QgsMessageLog.logMessage("💾 保存ボタンクリック", "PhotoEditor", Qgis.Info)
        self._save_image()
    
    def _on_color_clicked(self):
        """色ボタンクリック"""
        QgsMessageLog.logMessage("🎨 色ボタンクリック", "PhotoEditor", Qgis.Info)
        self._choose_color()
    
    def _on_fit_clicked(self):
        """フィットボタンクリック"""
        QgsMessageLog.logMessage("🔍 フィットボタンクリック", "PhotoEditor", Qgis.Info)
        self._fit_to_view()
    
    def _update_color_button(self):
        """色ボタンの見た目を更新"""
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color.name()};
                border: 2px solid #333;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: #007AFF;
            }}
        """)
    
    def _on_tool_button_clicked(self, button):
        """ツールボタンがクリックされた時"""
        QgsMessageLog.logMessage(
            f"🔧 ツールボタンクリック: {button.text()} / {button.toolTip()}",
            "PhotoEditor", Qgis.Info
        )
        # ボタンからツールIDを逆引き
        for tool_id, btn in self.tool_buttons.items():
            if btn == button:
                self._set_tool(tool_id)
                break
    
    def _set_tool(self, tool):
        """ツール変更"""
        self.current_tool = tool
        
        # 選択ツールの場合はドラッグモードをスクロールに
        if tool == DrawingTool.SELECT:
            self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        
        QgsMessageLog.logMessage(
            f"ツール変更: {tool}",
            "PhotoEditor", Qgis.Info
        )
    
    def _choose_color(self):
        """色選択ダイアログ"""
        color = QColorDialog.getColor(self.current_color, self.widget, "描画色を選択")
        if color.isValid():
            self.current_color = color
            self._update_color_button()
            QgsMessageLog.logMessage(
                f"色変更: {color.name()}",
                "PhotoEditor", Qgis.Info
            )
    
    def _set_line_width(self, width):
        """線幅変更"""
        self.line_width = width
    
    def _delete_selected(self):
        """選択アイテム削除"""
        for item in self.graphics_scene.selectedItems():
            if item != self.pixmap_item:  # 背景画像は削除しない
                self.graphics_scene.removeItem(item)
        QgsMessageLog.logMessage("選択アイテム削除", "PhotoEditor", Qgis.Info)
    
    def _clear_drawings(self):
        """全描画削除（背景画像以外）"""
        items_to_remove = []
        for item in self.graphics_scene.items():
            if item != self.pixmap_item:
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.graphics_scene.removeItem(item)
        
        QgsMessageLog.logMessage(
            f"全描画削除: {len(items_to_remove)}個のアイテム",
            "PhotoEditor", Qgis.Info
        )
    
    def _save_image(self):
        """編集済み画像を保存"""
        if not self.current_photo_path:
            self.status_label.setText("⚠ 保存する画像がありません")
            self.status_label.setStyleSheet("color: #FF9500;")
            return
        
        try:
            # シーン内のアイテム数を確認
            all_items = self.graphics_scene.items()
            QgsMessageLog.logMessage(
                f"シーン内アイテム数: {len(all_items)}",
                "PhotoEditor", Qgis.Info
            )
            for i, item in enumerate(all_items):
                QgsMessageLog.logMessage(
                    f"  アイテム{i}: {type(item).__name__}, zValue={item.zValue()}, visible={item.isVisible()}",
                    "PhotoEditor", Qgis.Info
                )
            
            # シーンの範囲を取得
            scene_rect = self.graphics_scene.sceneRect()
            QgsMessageLog.logMessage(
                f"シーン範囲: {scene_rect.width()}x{scene_rect.height()}",
                "PhotoEditor", Qgis.Info
            )
            
            # 方法: QGraphicsViewからグラブ
            # まずビューをシーン全体にフィット
            self.graphics_view.fitInView(scene_rect, Qt.KeepAspectRatio)
            
            # ビューポートのサイズでQPixmapを作成
            # シーンのサイズで画像を作成
            width = int(scene_rect.width())
            height = int(scene_rect.height())
            
            # QPixmapを作成
            pixmap = QPixmap(width, height)
            pixmap.fill(QColor(255, 255, 255))
            
            # QPainterでシーンを描画
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)
            
            # 背景を白で塗りつぶし
            painter.fillRect(0, 0, width, height, QColor(255, 255, 255))
            
            # シーンをレンダリング
            self.graphics_scene.render(
                painter,
                QRectF(0, 0, width, height),  # ターゲット
                scene_rect                     # ソース
            )
            painter.end()
            
            QgsMessageLog.logMessage(
                f"レンダリング完了: pixmap.isNull()={pixmap.isNull()}, size={pixmap.width()}x{pixmap.height()}",
                "PhotoEditor", Qgis.Info
            )
            
            # 保存先パス生成
            original_path = Path(self.current_photo_path)
            original_path_str = str(original_path)
            
            # /original/ を /edited/ に置換
            if '/original/' in original_path_str:
                edited_path_str = original_path_str.replace('/original/', '/edited/')
                edited_path = Path(edited_path_str)
            else:
                edited_dir = original_path.parent.parent / "edited"
                edited_path = edited_dir / original_path.name
            
            # ディレクトリを作成
            edited_path.parent.mkdir(parents=True, exist_ok=True)
            
            QgsMessageLog.logMessage(
                f"保存先: {edited_path}",
                "PhotoEditor", Qgis.Info
            )
            
            # QPixmapをQImageに変換して保存
            image = pixmap.toImage()
            
            # JPEG保存
            if image.save(str(edited_path), "JPEG", 90):
                self.status_label.setText(f"✓ 保存完了: {edited_path.name}")
                self.status_label.setStyleSheet("color: #34C759;")
                QgsMessageLog.logMessage(
                    f"画像保存成功: {edited_path}",
                    "PhotoEditor", Qgis.Info
                )
                
                # photo_edited_path フィールド更新
                self._update_edited_path_field(str(edited_path))
            else:
                raise Exception("画像保存に失敗")
            
        except Exception as e:
            self.status_label.setText(f"❌ 保存エラー: {str(e)}")
            self.status_label.setStyleSheet("color: #FF3B30;")
            QgsMessageLog.logMessage(
                f"画像保存エラー: {str(e)}",
                "PhotoEditor", Qgis.Critical
            )
            import traceback
            QgsMessageLog.logMessage(
                f"トレースバック: {traceback.format_exc()}",
                "PhotoEditor", Qgis.Critical
            )
    
    def _update_edited_path_field(self, edited_path):
        """photo_edited_path フィールドを更新"""
        try:
            feature = self._current_feature
            if not feature:
                return
            
            layer = self.layer()
            if not layer:
                return
            
            field_names = feature.fields().names()
            if 'photo_edited_path' not in field_names:
                QgsMessageLog.logMessage(
                    "photo_edited_path フィールドが存在しません",
                    "PhotoEditor", Qgis.Warning
                )
                return
            
            # フィールドインデックス取得
            field_idx = feature.fields().indexOf('photo_edited_path')
            
            # レイヤーを編集モードにして更新
            was_editing = layer.isEditable()
            if not was_editing:
                layer.startEditing()
            
            layer.changeAttributeValue(feature.id(), field_idx, edited_path)
            
            if not was_editing:
                layer.commitChanges()
            
            QgsMessageLog.logMessage(
                f"photo_edited_path 更新: {edited_path}",
                "PhotoEditor", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"フィールド更新エラー: {str(e)}",
                "PhotoEditor", Qgis.Warning
            )
    
    def initWidget(self, editor):
        """初期化"""
        self.status_label.setText("✓ 初期化完了")
    
    def setFeature(self, feature):
        """地物がセットされた時"""
        super().setFeature(feature)
        self._current_feature = feature
        QgsMessageLog.logMessage("setFeature() 呼び出し", "PhotoEditor", Qgis.Info)
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
        QgsMessageLog.logMessage("=== load_photo() 開始 ===", "PhotoEditor", Qgis.Info)
        try:
            # 地物取得
            feature = None
            try:
                feature = self.formFeature()
            except AttributeError:
                if hasattr(self, '_current_feature'):
                    feature = self._current_feature
            except Exception as e:
                QgsMessageLog.logMessage(f"formFeature()エラー: {str(e)}", "PhotoEditor", Qgis.Warning)
            
            if not feature or not feature.isValid():
                self.status_label.setText("⚠ 地物が選択されていません")
                self.status_label.setStyleSheet("color: #FF9500;")
                return
            
            photo_path = self._get_photo_path(feature)
            
            if not photo_path:
                self.status_label.setText("⚠ 写真パスが取得できません")
                self.status_label.setStyleSheet("color: #FF9500;")
                return
            
            if not os.path.exists(photo_path):
                self.status_label.setText("❌ ファイルが見つかりません")
                self.status_label.setStyleSheet("color: #FF3B30;")
                return
            
            pixmap = self._load_image_as_pixmap(photo_path)
            
            if pixmap is None or pixmap.isNull():
                self.status_label.setText("❌ 画像の読み込みに失敗")
                self.status_label.setStyleSheet("color: #FF3B30;")
                return
            
            # シーンをクリアして新しい画像を追加
            self.graphics_scene.clear()
            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.pixmap_item.setZValue(-1)  # 背景として最背面に
            self.graphics_scene.addItem(self.pixmap_item)
            
            # シーン範囲設定
            rect = pixmap.rect()
            self.graphics_scene.setSceneRect(QRectF(rect.x(), rect.y(), rect.width(), rect.height()))
            
            # フィット
            QTimer.singleShot(100, lambda: self._fit_to_view())
            
            self.current_photo_path = photo_path
            self.status_label.setText(f"✓ {os.path.basename(photo_path)}")
            self.status_label.setStyleSheet("color: #34C759;")
            
            QgsMessageLog.logMessage(
                f"画像読み込み成功: {pixmap.width()}x{pixmap.height()}",
                "PhotoEditor", Qgis.Info
            )
            
        except Exception as e:
            self.status_label.setText(f"❌ エラー: {str(e)}")
            self.status_label.setStyleSheet("color: #FF3B30;")
            QgsMessageLog.logMessage(f"画像読み込みエラー: {str(e)}", "PhotoEditor", Qgis.Critical)
    
    def _load_image_as_pixmap(self, photo_path):
        """画像をQPixmapとして読み込む"""
        try:
            qimage = QImage(photo_path)
            if not qimage.isNull():
                qimage = qimage.convertToFormat(QImage.Format_RGB32)
                pixmap = QPixmap.fromImage(qimage)
                QgsMessageLog.logMessage(f"画像読み込み成功: depth={pixmap.depth()}", "PhotoEditor", Qgis.Info)
                return pixmap
        except Exception as e:
            QgsMessageLog.logMessage(f"画像読み込み失敗: {str(e)}", "PhotoEditor", Qgis.Warning)
        return None
    
    def _get_photo_path(self, feature):
        """地物から写真パスを取得"""
        field_names = feature.fields().names()
        path_fields = ['photo_original_path', 'photo_path']
        
        for field_name in path_fields:
            if field_name in field_names:
                path = feature[field_name]
                if path and str(path).strip():
                    photo_path = str(path).strip()
                    QgsMessageLog.logMessage(f"写真パス取得 ({field_name}): {photo_path}", "PhotoEditor", Qgis.Info)
                    return photo_path
        
        return None
