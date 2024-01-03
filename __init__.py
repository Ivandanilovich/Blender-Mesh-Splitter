bl_info = {
    "name" : "Mesh Splitter by vertex groups",
    "author" : "ivand",
    "description" : "",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 1),
    "location" : "",
    "warning" : "",
    "category" : "Object"
}

import bpy
import bmesh
import numpy as np

# Function to walk the boundary loop from a given edge
def walk_boundary_loop(edge):
    loop_verts = []
    vert = edge.verts[0]
    while True:
        loop_verts.append(vert)
        # Try to find the next boundary edge that is not the current one
        next_edge = next((e for e in vert.link_edges if e.is_boundary and e != edge), None)
        if next_edge is None:
            break
        # Move to the next vertex of the edge
        vert = next_edge.other_vert(vert)
        # If we have come back to the start, the loop is closed
        if vert in loop_verts:
            break
        edge = next_edge
    return loop_verts

def clear_mesh(obj):
        # Set the area threshold to determine small faces, which might indicate internal faces
    area_threshold = 0.001

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    # Get the mesh data
    mesh = bmesh.from_edit_mesh(obj.data)
    
    # Collect vertices to remove
    verts_to_remove = [v for v in mesh.verts if all(face.calc_area() < area_threshold for face in v.link_faces)]

    # Select vertices for deletion
    bmesh.ops.delete(mesh, geom=verts_to_remove, context='VERTS')

    # Update the mesh
    bmesh.update_edit_mesh(obj.data)
    
    bpy.ops.object.mode_set(mode='OBJECT')

class MeshSplitter(bpy.types.Operator):
    bl_idname = "object.split_by_vertex_groups"
    bl_label = "Mesh Splitter by vertex groups"

    def split_verts_indexes_by_group(self, obj, weight_threshold=0.5):
        d = {g.index:[] for g in obj.vertex_groups}
        d['def'] = []

        for vertex in obj.data.vertices:
            inds = [g.group for g in vertex.groups]
            weights = [g.weight for g in vertex.groups]
            i = np.argmax(weights)
            weight = weights[i]
            group_id = inds[i]
            if weight<weight_threshold:
                # print(weights, np.sum(weights))
                # d["def"].append(vertex.index)
                continue
            d[group_id].append(vertex.index)
        return d

    def select_object(self, obj):
        # Select the object
        obj.select_set(True)

        # Make the object the active one
        bpy.context.view_layer.objects.active = obj

    def select_verts_and_split_object(self, obj, indexes, new_object_name):
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
        bpy.ops.object.editmode_toggle()

        for idx in indexes:
            obj.data.vertices[idx].select = True
            
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.duplicate()
        bpy.ops.mesh.separate(type='SELECTED')
        
        separated_object = [ob for ob in bpy.context.selected_objects if ob.name != obj.name][0]
        separated_object.name = new_object_name
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        return separated_object

    def fill_holes(self, obj):
        bpy.ops.object.select_all(action='DESELECT')
        self.select_object(obj)

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)

        already_visited = set()
        for edge in bm.edges:
            if edge.is_boundary and edge not in already_visited:
                loop_verts = walk_boundary_loop(edge)
                bpy.ops.mesh.select_all(action='DESELECT')
                for vert in loop_verts:
                    vert.select = True
                    # Mark the edges as visited
                    for e in vert.link_edges:
                        if e.is_boundary:
                            already_visited.add(e)
                # Flush the selection to make it update in the viewport
                bm.select_flush(True)
                # Perform this to see the selection in the viewport for the current loop
                bmesh.update_edit_mesh(obj.data)
                bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, 0)})
                bpy.ops.mesh.merge(type='CENTER')
        bpy.ops.object.mode_set(mode='OBJECT')

    def execute(self, context):
        
        obj = bpy.context.object
        obj_name = obj.name
        
        if not obj.type == 'MESH':
            raise Exception('Object should be a mesh')
        if not obj.vertex_groups:
            raise Exception('Object should have vertex groups')
        
        groups_names = [i.name for i in obj.vertex_groups]

        d = self.split_verts_indexes_by_group(obj)
        for i,j in d.items():
            bpy.ops.object.select_all(action='DESELECT')
            self.select_object(bpy.data.objects[obj_name])
            if len(j)<4:
                continue

            new_ob = self.select_verts_and_split_object(bpy.data.objects[obj_name], j, new_object_name=f"{obj_name}_{groups_names[i]}")
            self.fill_holes(new_ob)
            clear_mesh(new_ob)

        return {'FINISHED'}

class VIEW3D_PT_CustomPanel(bpy.types.Panel):
    bl_label = "Custom Mesh Splitter Panel"
    bl_idname = "VIEW3D_PT_custom_mesh_splitter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        # Add a button that calls the MeshSplitter operator
        layout.operator("object.split_by_vertex_groups", text="Split by Vertex Groups")

def register():
    bpy.utils.register_class(MeshSplitter)
    bpy.utils.register_class(VIEW3D_PT_CustomPanel)

def unregister():
    bpy.utils.unregister_class(MeshSplitter)
    bpy.utils.unregister_class(VIEW3D_PT_CustomPanel)

if __name__ == "__main__":
    register()


