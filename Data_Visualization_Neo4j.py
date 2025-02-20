import sys
import unreal
import py2neo
from uuid import uuid4
from py2neo import Graph
from pprint import pprint

# Ensure Python site-packages is included in sys.path
PYTHON_PACKAGES_PATH = 'C:\\Shards\\Plateform\\Python39\\Lib\\site-packages'
if PYTHON_PACKAGES_PATH not in sys.path:
    sys.path.append(PYTHON_PACKAGES_PATH)

# Neo4j Database Connection Class
class Neo4jQueryApplier:
    def __init__(self):
        # Initialize the connection to the Neo4j graph database
        self.graph = Graph("bolt://localhost:7687", auth=('neo4j', 'shardsdb'))

    def create_item(self, label, uuid):
        query = f"merge(n:{label}" + "{uuid: " + f"'{uuid}'" + "})"
        self.execute_query(query)

    def execute_query(self, query):
        return self.graph.run(query)

    def set_item_properties(self, uuid, properties):
        for key, value in properties.items():
            list_contains = []
            if type(value) == list:
                for i in value:
                    t = type(i)
                    if t not in list_contains:
                        list_contains.append(t)
                if len(list_contains) != 1:
                    if list_contains == [int, float] or list_contains == [float, int]:
                        pass
                    else:
                        raise TypeError(f"List {key} contain more than one type of elements")

        query = f"match(n) where n.uuid = '{uuid}' "
        for key, value in properties.items():
            if type(value) == str:
                query += f"set n.{key} = '{value}' "
            elif type(value) == int or type(value) == float:
                query += f"set n.{key} = {value} "
            elif type(value) == list:
                query += f"set n.{key} = ["
                for i in value:
                    if type(i) == str:
                        query += f'"{i}", '
                    if type(i) == int or type(i) == float:
                        query += f'{str(i)}, '
                query = query.rstrip(", ")
                query += "] "

            else:
                pass

        self.execute_query(query)

    def create_link(self, uuid01, uuid02, title):
        query = (f"match(n), (m) where n.uuid = '" + uuid01 + "' and m.uuid = '" + uuid02 + 
                f"' \n merge(n)-[:{title}]->(m) return n")
        self.execute_query(query)

# Initialize Neo4j Applier
applier = Neo4jQueryApplier()

# Unreal Content Browser Paths
UNREAL_CONTENT_BROWSER_PATHS = {
    "meshes": "/Game/Assets/BG/",
    "materials": "/Game/Assets/MAT/",
    "textures": "/Game/Assets/TEX/"
}

# List of Material Parameters to Check
LIST_MATERIAL_PARAMETERS = ["Map - Diffuse", "Map - Roughness", "Map - Normal", "Map - Metallic"]

# Get all actors in the level
all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
mesh_actor_dict = {}

# Process Meshes
def process_meshes():
    for prop_folder_path in unreal.EditorAssetLibrary.list_assets(UNREAL_CONTENT_BROWSER_PATHS["meshes"], recursive=False, include_folder=True):
        if unreal.EditorAssetLibrary.does_directory_exist(prop_folder_path):
            meshes_folder = f"{prop_folder_path}Meshes/"
            if unreal.EditorAssetLibrary.does_directory_exist(meshes_folder):
                for asset_name in unreal.EditorAssetLibrary.list_assets(meshes_folder, recursive=False, include_folder=False):
                    asset = unreal.EditorAssetLibrary.load_asset(asset_name)
                    uuid_mesh = str(uuid4())
                    mesh_name = asset_name.rsplit('.', 1)[1]
                    applier.create_item("Mesh", uuid_mesh)
                    applier.set_item_properties(uuid_mesh, {"name": mesh_name})
                    mesh_material_component = asset.get_material(0)
                    mesh_material_name = mesh_material_component.get_name()
                    mesh_actor_dict[uuid_mesh] = {"type": "Mesh", "material": mesh_material_name}
                    
                    for actor in all_actors:
                        if actor.get_class().get_name() == "StaticMeshActor":
                            static_mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
                            if static_mesh_component and static_mesh_component.static_mesh.get_name() == mesh_name:
                                uuid_actor = str(uuid4())
                                mesh_actor_dict[uuid_actor] = {"type": "Actor", "material": mesh_material_name}
                                applier.create_item("Actor", uuid_actor)
                                applier.set_item_properties(uuid_actor, {"name": mesh_name})
                                applier.create_link(uuid_mesh, uuid_actor, "CREATED_INSTANCE")

# Process Materials
def process_materials():
    for material_folder in unreal.EditorAssetLibrary.list_assets(UNREAL_CONTENT_BROWSER_PATHS["materials"], recursive=False, include_folder=True):
        if unreal.EditorAssetLibrary.does_directory_exist(material_folder):
            for material_name in unreal.EditorAssetLibrary.list_assets(material_folder, recursive=False, include_folder=False):
                asset = unreal.EditorAssetLibrary.load_asset(material_name)
                uuid_material = str(uuid4())
                material_name_clean = material_name.rsplit('.', 1)[1]
                applier.create_item("Material", uuid_material)
                applier.set_item_properties(uuid_material, {"name": material_name_clean})
                
                for mesh_uuid, data in mesh_actor_dict.items():
                    if data["material"] == material_name_clean:
                        applier.create_link(mesh_uuid, uuid_material, "HAS_MATERIAL")

                process_textures(uuid_material, asset)

# Process Textures
def process_textures(uuid_material, material_asset):
    for param in LIST_MATERIAL_PARAMETERS:
        texture = material_asset.get_texture_parameter_value(param)
        if texture:
            texture_name = texture.get_name()
            
            for texture_folder in unreal.EditorAssetLibrary.list_assets(UNREAL_CONTENT_BROWSER_PATHS["textures"], recursive=False, include_folder=True):
                if unreal.EditorAssetLibrary.does_directory_exist(texture_folder):
                    textures_subfolder = f"{texture_folder}Textures/"
                    if unreal.EditorAssetLibrary.does_directory_exist(textures_subfolder):
                        for texture_asset in unreal.EditorAssetLibrary.list_assets(textures_subfolder, recursive=False, include_folder=False):
                            texture_asset_name = texture_asset.rsplit('.', 1)[1]
                            if texture_name == texture_asset_name:
                                uuid_texture = str(uuid4())
                                applier.create_item("Texture", uuid_texture)
                                applier.set_item_properties(uuid_texture, {"name": texture_asset_name})
                                applier.create_link(uuid_material, uuid_texture, "USES_TEXTURE")

# Run Processing Functions
process_meshes()
process_materials()
