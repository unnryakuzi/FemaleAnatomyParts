# -*- coding: utf-8 -*-
""".blend を開いたとき、パーツをクリックで選べる画面にする（2026-10-18）

女性マスターは「Modeling」タブで開き、そのビューポートのオーバーレイがオフ、オブジェクトモードのツールが「回転」のまま
保存されていた（過去の撮影でオーバーレイを切ったまま保存したもの）。この状態だとクリックで選んでも縁取りが出ず、
選べないように見える。配布 .blend（v1.67.0 / v1.68.0）も同じだった。
  - 全ワークスペースの 3D ビューで、オーバーレイと「選択物の輪郭」をオンにする
  - オブジェクトモードのツールが選択系でないワークスペースは「選択（ボックス）」にする
表示・非表示（目のアイコン）と視点は触らない。

  import ui_defaults; ui_defaults.apply()   # バックグラウンド（-b）でも動く。保存は呼び出し側で
"""
import bpy

SELECT_TOOLS = {"builtin.select", "builtin.select_box", "builtin.select_circle", "builtin.select_lasso"}


class _Ctx:
    """activate_by_id が読む workspace / mode / space_data だけ差し替える（-b では context.workspace を切り替えられない）"""

    def __init__(self, workspace, space):
        self.workspace = workspace
        self.mode = "OBJECT"
        self.space_data = space

    def __getattr__(self, k):
        return getattr(bpy.context, k)


def apply():
    from bl_ui.space_toolsystem_common import activate_by_id
    n_overlay = 0
    for scr in bpy.data.screens:
        for a in scr.areas:
            for s in a.spaces:
                if s.type != "VIEW_3D":
                    continue
                if not (s.overlay.show_overlays and s.overlay.show_outline_selected):
                    n_overlay += 1
                s.overlay.show_overlays = True
                s.overlay.show_outline_selected = True
    tools = []
    for ws in bpy.data.workspaces:
        t = ws.tools.from_space_view3d_mode("OBJECT", create=False)
        if t is None or t.idname in SELECT_TOOLS:
            continue
        space = next((s for scr in ws.screens for a in scr.areas for s in a.spaces if s.type == "VIEW_3D"), None)
        old = t.idname
        if activate_by_id(_Ctx(ws, space), "VIEW_3D", "builtin.select_box"):
            tools.append("%s: %s -> %s" % (ws.name, old, ws.tools.from_space_view3d_mode("OBJECT").idname))
    print("[ui_defaults] オーバーレイをオンにした 3D ビュー %d 個 / ツールを選択にしたワークスペース %s" % (n_overlay, tools or "なし"))
    return n_overlay, tools
