import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math
import sys
import os # Import the os module
from asteroid_3d_module import Asteroid3D, MAX_OUTER_RADIUS

# --- Display Settings ---
DISPLAY_WIDTH = 1920
DISPLAY_HEIGHT = 1080

# --- Track Settings ---
TRACK_RADIUS = 200.0
TRACK_CENTER_Y = -100.0 # Slightly below center for isometric view
TRACK_SEGMENTS = 100 # Number of line segments to draw the circle

# --- Asteroid Settings ---
NUM_ASTEROIDS_ON_TRACK = 1
ASTEROID_TRACK_SPEED = 0.005 # radians per second

# --- Texture Loading Function for OpenGL (Copied from test_3d_asteroid_viewer.py) ---
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

# --- Main Drawing Function (Copied from test_3d_asteroid_viewer.py) ---
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

    # Draw satellites recursively (if any)
    for satellite in asteroid.satellites:
        draw_asteroid(satellite)

def draw_track():
    glColor3f(0.5, 0.5, 0.5) # Grey color for the track
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    for i in range(TRACK_SEGMENTS):
        angle = 2 * math.pi * i / TRACK_SEGMENTS
        x = TRACK_RADIUS * math.cos(angle)
        z = TRACK_RADIUS * math.sin(angle)
        glVertex3f(x, TRACK_CENTER_Y, z)
    glEnd()

def main():
    pygame.init()
    pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Isometric Asteroid Track")

    # --- OpenGL Setup ---
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    glLightfv(GL_LIGHT0, GL_POSITION, (0, 0, 1, 0)) # Directional light from the front
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.4, 0.4, 0.4, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))

    gluPerspective(45, (DISPLAY_WIDTH / DISPLAY_HEIGHT), 0.1, 1000.0)
    # Adjust camera for isometric-like view
    glTranslatef(0.0, 0.0, -500)
    glRotatef(30, 1, 0, 0) # Pitch down
    glRotatef(45, 0, 1, 0) # Yaw

    # --- Load Texture (re-using existing asteroid texture) ---
    try:
        texture_path = os.path.join("assets", 'clear_asteroid_texture.png')
        asteroid_texture_id = load_texture(texture_path)
    except Exception as e:
        print(f"Could not load texture: {e}")
        asteroid_texture_id = glGenTextures(1) # Fallback

    # --- Create Asteroids for the Track ---
    asteroids = []
    main_asteroid_radius = 30 # Fixed size for the main asteroid
    satellite_proportion = 0.05 # 5% of main asteroid size

    for i in range(NUM_ASTEROIDS_ON_TRACK):
        # Distribute asteroids evenly along the track initially
        initial_angle = 2 * math.pi * i / NUM_ASTEROIDS_ON_TRACK
        x = TRACK_RADIUS * math.cos(initial_angle)
        z = TRACK_RADIUS * math.sin(initial_angle)
        
        # Calculate satellite size based on main asteroid radius
        min_satellite_size = main_asteroid_radius * satellite_proportion * 0.8
        max_satellite_size = main_asteroid_radius * satellite_proportion * 1.2

        asteroid = Asteroid3D(x, TRACK_CENTER_Y, z, 
                              new_outer_radius=main_asteroid_radius, 
                              texture_id=asteroid_texture_id, 
                              satellite_size_range=(min_satellite_size, max_satellite_size),
                              nested_satellite_proportion=satellite_proportion) # Pass the proportion # Exactly 5% of main asteroid size
        asteroid.track_angle = initial_angle # Store current position on track
        asteroid.track_speed = ASTEROID_TRACK_SPEED # Store speed
        asteroids.append(asteroid)

    # --- Mouse Control Variables (from previous viewer) ---
    mouse_dragging = False
    last_mouse_pos = (0, 0)

    clock = pygame.time.Clock()
    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_dragging = True
                last_mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_dragging = False
            elif event.type == pygame.MOUSEMOTION and mouse_dragging:
                dx, dy = event.pos[0] - last_mouse_pos[0], event.pos[1] - last_mouse_pos[1]
                last_mouse_pos = event.pos
                # Apply rotation to the entire scene for camera control
                glRotatef(dx, 0, 1, 0) # Yaw
                glRotatef(dy, 1, 0, 0) # Pitch

        # --- Update Asteroid Positions on Track ---
        for asteroid in asteroids:
            asteroid.track_angle += asteroid.track_speed * delta_time
            x = TRACK_RADIUS * math.cos(asteroid.track_angle)
            z = TRACK_RADIUS * math.sin(asteroid.track_angle)
            asteroid.position = np.array([x, TRACK_CENTER_Y, z])
            asteroid.update(delta_time, asteroid.position) # Update asteroid's self-rotation

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # --- Draw Track ---
        draw_track()

        # --- Draw Asteroids ---
        for asteroid in asteroids:
            draw_asteroid(asteroid)

        pygame.display.flip()
        pygame.time.wait(10) # Small delay to prevent 100% CPU usage

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()