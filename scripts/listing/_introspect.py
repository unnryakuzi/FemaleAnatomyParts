import bpy
def main():
    sc = bpy.context.scene
    vl = bpy.context.view_layer
    print("=== FILE:", bpy.data.filepath)
    print("=== view_transform:", sc.view_settings.view_transform)
    def walk(col, depth=0):
        print(f"COL {'  '*depth}{col.name}  (all={len(col.all_objects)}, direct={len(col.objects)})")
        for ch in col.children:
            walk(ch, depth+1)
    walk(sc.collection)
    # layer collection hide/exclude states (top level)
    def lcwalk(lc, depth=0):
        print(f"LC {'  '*depth}{lc.name}  exclude={lc.exclude} hide_vp={lc.hide_viewport}")
        for ch in lc.children:
            lcwalk(ch, depth+1)
    lcwalk(vl.layer_collection)
    # breast / skin / organ / vessel / nerve object hints
    import re
    pat = re.compile(r'胸|乳|Breast|外皮|skin|Skin|臓|内臓|organ|Organ|血管|静脈|動脈|vessel|Vessel|神経|nerve|Nerve|皮膚')
    hits = [(o.name, o.users_collection[0].name if o.users_collection else '?', o.hide_render, o.hide_get()) for o in sc.objects if pat.search(o.name)]
    print("=== name-hint objects (name | col | hide_render | hide_get):", len(hits))
    for h in hits[:40]:
        print("OBJ", h)
if __name__=="__main__":
    main()
