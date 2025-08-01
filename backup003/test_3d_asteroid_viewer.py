import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from asteroid_3d_module import Asteroid3D, MAX_OUTER_RADIUS
import os
import random # Import the random module
import sys # Import the sys module

# --- Collision Cooldown ---
COLLISION_COOLDOWN = 1000 # milliseconds

# --- Asset Path ---
ASSET_PATH = "assets"

# --- Texture Loading Function for OpenGL ---
def load_texture(filename):
    texture_surface = pygame.image.load(filename)
    texture_data = pygame.image.tostring(texture_surface, "RGBA", 1)
    width = texture_surface.get_width()
    height = texture_surface.get_height()

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    gluBuild2DMipmaps(GL_TEXTURE_2D, GL_RGBA, width, height, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    return texture_id

# --- Main Drawing Function ---
def draw_asteroid(asteroid):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, asteroid.texture_id)

    glPushMatrix()
    # Apply the asteroid's position and rotation
    glTranslatef(asteroid.position[0], asteroid.position[1], asteroid.position[2])
    
    # Convert the 3x3 rotation matrix from scipy to a 4x4 matrix for OpenGL
    rotation_matrix_3x3 = asteroid.rotation.as_matrix()
    rotation_matrix_4x4 = np.identity(4, dtype=np.float32)
    rotation_matrix_4x4[:3, :3] = rotation_matrix_3x3
    glMultMatrixf(rotation_matrix_4x4.T) # Use transpose for OpenGL

    # Set color and material properties
    color = asteroid.get_color()
    glColor4f(color[0]/255.0, color[1]/255.0, color[2]/255.0, 1.0)
    glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, (color[0]/255.0, color[1]/255.0, color[2]/255.0, 1.0))

    # Draw the faces
    glBegin(GL_TRIANGLES)
    for face in asteroid.faces:
        for vertex_index in face:
            glNormal3fv(asteroid.base_vertices[vertex_index]) # Use vertex position as normal for smooth shading
            glTexCoord2fv(asteroid.uv_coords[vertex_index])
            glVertex3fv(asteroid.base_vertices[vertex_index])
    glEnd()

    glPopMatrix()
    glDisable(GL_TEXTURE_2D)

# --- Main Function ---
def main():
    pygame.init()
    display = (1920, 1080)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("OpenGL Asteroid Viewer - Click and Drag to Rotate")

    # --- OpenGL Setup ---
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    glLightfv(GL_LIGHT0, GL_POSITION, (0, 0, 1, 0)) # Directional light from the front
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.4, 0.4, 0.4, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))

    gluPerspective(45, (display[0] / display[1]), 0.1, 1000.0)
    glTranslatef(0.0, 0.0, -500) # Move camera back

    # --- Load Texture Once ---
    try:
        texture_path = os.path.join(ASSET_PATH, 'clear_asteroid_texture.png')
        asteroid_texture_id = load_texture(texture_path)
    except Exception as e:
        print(f"Could not load texture: {e}")
        asteroid_texture_id = glGenTextures(1)

    # --- Create Initial Asteroid ---
    asteroid = Asteroid3D(0, 0, 0, texture_id=asteroid_texture_id)
    asteroid.texture_id = asteroid_texture_id

    # --- Mouse Control Variables ---
    mouse_dragging = False
    last_mouse_pos = (0, 0)

    # --- Rotation Control Variable ---
    is_spinning = True # Asteroid spins by default

    # --- Jaggedness Control Variable ---
    current_jaggedness_factor = 1.0 # Initial jaggedness
    JAGGEDNESS_STEP = 0.5
    MAX_JAGGEDNESS = 5.0
    MIN_JAGGEDNESS = 0.5

    # --- Displacement Control Variable ---
    current_displacement_strength = 0.0 # Initial displacement
    DISPLACEMENT_STEP = 5.0
    MAX_DISPLACEMENT = 500.0
    MIN_DISPLACEMENT = -500.0 # Allow for both indents and bumps

    # --- Collision Cooldown ---
    # COLLISION_COOLDOWN = 500 # milliseconds # Moved to global scope

    # --- Shape Randomization Control Variable ---
    current_shape_randomization_factor = (1.0, 1.0, 1.0) # Initial shape (spherical)

    clock = pygame.time.Clock() # Initialize clock
    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0 # Limit to 60 FPS and get delta time in seconds
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == K_SPACE:
                    # Create a new random asteroid with the current jaggedness and displacement factors
                    asteroid = Asteroid3D(0, 0, 0, jaggedness_factor=current_jaggedness_factor, displacement_strength=current_displacement_strength, shape_randomization_factor=current_shape_randomization_factor, texture_id=asteroid_texture_id)
                    asteroid.texture_id = asteroid_texture_id
                elif event.key == K_UP:
                    current_jaggedness_factor = min(MAX_JAGGEDNESS, current_jaggedness_factor + JAGGEDNESS_STEP)
                    print(f"Jaggedness: {current_jaggedness_factor:.1f}")
                    # Recreate asteroid with new jaggedness
                    asteroid = Asteroid3D(0, 0, 0, new_outer_radius=asteroid.outer_radius, jaggedness_factor=current_jaggedness_factor, displacement_strength=current_displacement_strength, shape_randomization_factor=current_shape_randomization_factor, texture_id=asteroid_texture_id)
                    asteroid.texture_id = asteroid_texture_id
                elif event.key == K_DOWN:
                    current_jaggedness_factor = max(MIN_JAGGEDNESS, current_jaggedness_factor - JAGGEDNESS_STEP)
                    print(f"Jaggedness: {current_jaggedness_factor:.1f}")
                    # Recreate asteroid with new jaggedness
                    asteroid = Asteroid3D(0, 0, 0, new_outer_radius=asteroid.outer_radius, jaggedness_factor=current_jaggedness_factor, displacement_strength=current_displacement_strength, shape_randomization_factor=current_shape_randomization_factor, texture_id=asteroid_texture_id)
                    asteroid.texture_id = asteroid_texture_id
                elif event.key == K_PERIOD:
                    # Create the largest possible asteroid, using the same randomization logic as spacebar
                    # but forcing the outer radius to MAX_OUTER_RADIUS.
                    asteroid = Asteroid3D(0, 0, 0, new_outer_radius=MAX_OUTER_RADIUS, randomize_all=True, texture_id=asteroid_texture_id)
                    asteroid.texture_id = asteroid_texture_id
                elif event.key == K_s:
                    is_spinning = not is_spinning
                    print(f"Spinning: {is_spinning}")
                elif event.key == K_EQUALS: # Plus key
                    current_displacement_strength = min(MAX_DISPLACEMENT, current_displacement_strength + DISPLACEMENT_STEP)
                    print(f"Displacement: {current_displacement_strength:.1f}")
                    # Recreate asteroid with new displacement
                    asteroid = Asteroid3D(0, 0, 0, new_outer_radius=asteroid.outer_radius, jaggedness_factor=current_jaggedness_factor, displacement_strength=current_displacement_strength, shape_randomization_factor=current_shape_randomization_factor, texture_id=asteroid_texture_id)
                    asteroid.texture_id = asteroid_texture_id
                elif event.key == K_MINUS:
                    current_displacement_strength = max(MIN_DISPLACEMENT, current_displacement_strength - DISPLACEMENT_STEP)
                    print(f"Displacement: {current_displacement_strength:.1f}")
                    # Recreate asteroid with new displacement
                    asteroid = Asteroid3D(0, 0, 0, new_outer_radius=asteroid.outer_radius, jaggedness_factor=current_jaggedness_factor, displacement_strength=current_displacement_strength, shape_randomization_factor=current_shape_randomization_factor, texture_id=asteroid_texture_id)
                    asteroid.texture_id = asteroid_texture_id
                elif event.key == K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True
                last_mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False
            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                dx, dy = event.pos[0] - last_mouse_pos[0], event.pos[1] - last_mouse_pos[1]
                last_mouse_pos = event.pos
                glRotatef(dx, 0, 1, 0) # Yaw
                glRotatef(dy, 1, 0, 0) # Pitch

        if is_spinning:
            asteroid.update(delta_time, asteroid.position)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        draw_asteroid(asteroid)

        # Draw satellites
        for satellite in asteroid.satellites:
            draw_asteroid(satellite)

        pygame.display.flip()
        pygame.time.wait(10)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()