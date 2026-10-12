from pathlib import Path
import json, re, random, colorsys
from PIL import Image, ImageDraw

root = Path("_spacemod_build")
java = root / "src/main/java/com/spacemod"
resources = root / "src/main/resources"
assets = resources / "assets/spacemod"

def edit(rel, fn):
    path = java / rel
    text = path.read_text(encoding="utf-8")
    updated = fn(text)
    path.write_text(updated, encoding="utf-8")

def suits(s):
    if "import net.minecraft.world.item.ArmorItem;" not in s:
        s=s.replace("import net.minecraft.world.item.Item;", "import net.minecraft.world.item.Item;\nimport net.minecraft.world.item.ArmorItem;\nimport net.minecraft.world.item.ArmorMaterials;")
    for name in ("space_suit","basic_suit","heat_suit","cold_suit","pressure_suit","radiation_suit","toxic_suit","vacuum_suit","giant_suit","star_suit"):
        s=s.replace(f'reg("{name}", 1)',f'ITEMS.register("{name}", () -> new ArmorItem(ArmorMaterials.IRON, ArmorItem.Type.CHESTPLATE, new Item.Properties()))')
    return s
edit("ModItems.java",suits)

def telescope(s):
    for name in ("MARS","MOON","EUROPA"):
        s=s.replace(f"RocketEntity.{name}",f'RocketEntity.dim("{name.lower()}")')
    return s
edit("item/TelescopeItem.java",telescope)

def space(s):
    s=s.replace("level.getEntities().getAll().stream()","java.util.stream.StreamSupport.stream(level.getEntities().getAll().spliterator(), false)")
    old="player.teleportTo(space, 0.5, 80.0, 0.5, player.getYRot(), player.getXRot());"
    new="""net.minecraft.core.BlockPos center = new net.minecraft.core.BlockPos(0, 78, 0);
        for (int x = -5; x <= 5; x++) {
            for (int z = -5; z <= 5; z++) {
                net.minecraft.core.BlockPos pos = center.offset(x, 0, z);
                if (space.getBlockState(pos).isAir()) {
                    space.setBlock(pos, net.minecraft.world.level.block.Blocks.TINTED_GLASS.defaultBlockState(), 3);
                }
            }
        }
        player.teleportTo(space, 0.5, 79.2, 0.5, player.getYRot(), player.getXRot());"""
    return s.replace(old,new)
edit("world/OpenSpaceManager.java",space)

def rocket(s):
    s=s.replace("BlockPos pos = target.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, BlockPos.ZERO);","target.getChunk(0, 0);\n        BlockPos pos = target.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, BlockPos.ZERO);")
    return s.replace("pos.getY() + 1.5","Math.max(pos.getY() + 2.0, target.getMinBuildHeight() + 5.0)")
edit("entity/RocketEntity.java",rocket)

def boss(s):
    anchor="    @Override\n    public void tick() {"
    if "public boolean hurt(DamageSource source, float amount)" not in s:
        s=s.replace(anchor,"""    @Override
    public boolean hurt(DamageSource source, float amount) {
        if (source.getEntity() == null && !source.is(net.minecraft.tags.DamageTypeTags.BYPASSES_INVULNERABILITY)) return false;
        return super.hurt(source, amount);
    }

"""+anchor)
    return s
edit("boss/StarGuardianEntity.java",boss)

rough={"mars","mercury","pluto","moon","kepler_90i","cancri_e","wolf1061_c","trappist_1f"}
for file in (resources/"data/spacemod/dimension").glob("*.json"):
    obj=json.loads(file.read_text(encoding="utf-8"))
    gen=obj.get("generator",{})
    if gen.get("type")=="minecraft:noise" and file.stem in rough:
        gen["settings"]="minecraft:amplified"
    file.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

items=(java/"ModItems.java").read_text(encoding="utf-8")
names=set(re.findall(r'ITEMS\.register\("([a-z0-9_]+)"',items))
names.update(re.findall(r'\breg\("([a-z0-9_]+)"',items))
models=assets/"models/item"
textures=assets/"textures/item"
models.mkdir(parents=True,exist_ok=True)
textures.mkdir(parents=True,exist_ok=True)
for name in sorted(names):
    model=models/(name+".json")
    if not model.exists():
        model.write_text(json.dumps({"parent":"minecraft:item/generated","textures":{"layer0":f"spacemod:item/{name}"}},indent=2)+"\n")
    image_path=textures/(name+".png")
    if not image_path.exists():
        rng=random.Random(name)
        hue=rng.randrange(360)
        def rgb(h,l,s):
            return tuple(int(v*255) for v in colorsys.hls_to_rgb(h/360,l,s))
        bg=rgb(hue,.22,.5)
        fg=rgb((hue+42)%360,.64,.65)
        edge=rgb((hue+180)%360,.12,.6)
        image=Image.new("RGBA",(16,16),(0,0,0,0))
        draw=ImageDraw.Draw(image)
        draw.rounded_rectangle((2,2,13,13),radius=3,fill=bg+(255,),outline=edge+(255,),width=1)
        if "suit" in name or "armor" in name:
            draw.polygon([(5,3),(10,3),(13,7),(11,9),(11,13),(4,13),(4,9),(2,7)],fill=fg+(255,),outline=edge+(255,))
            draw.rectangle((6,4,9,7),fill=(55,110,160,255))
        elif any(t in name for t in ("ore","ingot","metal","crystal","gem","shard")):
            draw.polygon([(8,2),(13,7),(10,13),(5,12),(3,7)],fill=fg+(255,),outline=edge+(255,))
        else:
            draw.ellipse((4,4,11,11),fill=fg+(255,),outline=edge+(255,))
        image.save(image_path)
for model in (assets/"models/block").glob("*.json"):
    try: obj=json.loads(model.read_text(encoding="utf-8"))
    except ValueError: continue
    for ref in obj.get("textures",{}).values():
        if not isinstance(ref,str) or ref.startswith("#"): continue
        namespace,location=(ref.split(":",1) if ":" in ref else ("minecraft",ref))
        if namespace!="spacemod" or not location.startswith("block/"):continue
        target=assets/"textures"/(location+".png")
        if target.exists():continue
        rng=random.Random(location)
        base=tuple(rng.randrange(50,140) for _ in range(3))
        image=Image.new("RGB",(16,16),base)
        pixels=image.load()
        for y in range(16):
            for x in range(16):
                noise=rng.randrange(-25,26)
                pixels[x,y]=tuple(max(0,min(255,c+noise)) for c in base)
        target.parent.mkdir(parents=True,exist_ok=True)
        image.save(target)
print("Repair pass complete, items:",len(names))
