# -*- coding: utf-8 -*-
"""
Photo Editor Widget Plugin
プラグインエントリーポイント
"""


def classFactory(iface):
    """
    QGISがプラグインを読み込む際に呼ばれる関数
    
    Args:
        iface: QGISインターフェース
        
    Returns:
        PhotoEditorPlugin: プラグインインスタンス
    """
    from .photo_editor_plugin import PhotoEditorPlugin
    return PhotoEditorPlugin(iface)
