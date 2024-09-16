import pygame
import os
import time
import math
import random
import cv2
import mediapipe as mp
import HandTrackingModule as htm
pygame.font.init()

WIDTH, HEIGHT = 650, 650
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Shooter")

# Load images
RED_SPACE_SHIP = pygame.transform.scale(pygame.image.load(os.path.join("assets", "pixel_ship_red_small.png")),
                                         (30, 30))
GREEN_SPACE_SHIP =  pygame.transform.scale(pygame.image.load(os.path.join("assets", "pixel_ship_green_small.png")),
                                            (30, 30))
BLUE_SPACE_SHIP =  pygame.transform.scale(pygame.image.load(os.path.join("assets", "pixel_ship_blue_small.png")),
                                           (30, 30))

# Player ship
YELLOW_SPACE_SHIP = pygame.transform.scale(pygame.image.load(os.path.join("assets", "pixel_ship_yellow.png")),
                                            (40, 40))

# Lasers
RED_LASER = pygame.transform.scale(pygame.image.load(os.path.join("assets", "pixel_laser_red.png")),
                                      (30, 30))  
GREEN_LASER = pygame.transform.scale(pygame.image.load(os.path.join("assets", "pixel_laser_green.png")),
                                      (30, 30))   
BLUE_LASER = pygame.transform.scale(pygame.image.load(os.path.join("assets", "pixel_laser_blue.png")),
                                      (30, 30))  
YELLOW_LASER = pygame.transform.scale(pygame.image.load(os.path.join("assets", "pixel_laser_yellow.png")),
                                      (40, 40)) 

# Background
BG = pygame.transform.scale(pygame.image.load(os.path.join("assets", "background-black.png")), (WIDTH, HEIGHT))

# Initialize hand detector
detector = htm.handDetector()
SENSITIVITY = 1.5
dead_zone = 20

class Laser:
    def __init__(self, x, y, img):
        self.x = x
        self.y = y
        self.img = img
        self.mask = pygame.mask.from_surface(self.img)
    
    def draw(self, window):
        window.blit(self.img, (self.x, self.y))

    def move(self, vel):
        self.y += vel

    def off_screen(self, height):
        return not (self.y <= height and self.y >= 0)
    
    def collision(self, obj):
        return collide(self, obj)


class Ship():
    COOLDOWN = 30   

    def __init__(self, x, y, health=100):
        self.x = x
        self.y = y
        self.health = health
        self.ship_img = None
        self.laser_img = None
        self.lasers = []
        self.cool_down_counter = 0
    
    def draw(self, window):
        window.blit(self.ship_img, (self.x, self.y))
        for laser in self.lasers:
            laser.draw(window)

    def move_lasers(self, vel, obj):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            elif laser.collision(obj):
                obj.health -= 10
                self.lasers.remove(laser)

    def cooldown(self):
        if self.cool_down_counter >= self.COOLDOWN:
            self.cool_down_counter = 0
        elif self.cool_down_counter > 0:
            self.cool_down_counter += 1
    
    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1
    
    def get_width(self):
        return self.ship_img.get_width()

    def get_height(self):
        return self.ship_img.get_height()
    
    
class Player(Ship):
    def __init__(self, x, y, health=100):
        super().__init__(x, y, health)
        self.ship_img = YELLOW_SPACE_SHIP
        self.laser_img = YELLOW_LASER
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health 
    
    def move_lasers(self, vel, objs):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            else:
                for obj in objs:
                    if laser.collision(obj):
                        objs.remove(obj)
                        if laser in self.lasers:
                            self.lasers.remove(laser)

    def health_bar(self, window):
        pygame.draw.rect(window, (255, 0, 0), (self.x, self.y + self.ship_img.get_height() + 7,
                                                self.ship_img.get_width(), 5))
        pygame.draw.rect(window, (0, 255, 0), (self.x, self.y + self.ship_img.get_height() + 7,
                                                self.ship_img.get_width() * (self.health / self.max_health), 5))

    def draw(self, window):
        super().draw(window)
        self.health_bar(window)


class Enemy(Ship):
    COLOR_MAP = {
        "red": (RED_SPACE_SHIP, RED_LASER),
        "blue": (BLUE_SPACE_SHIP, BLUE_LASER),
        "green": (GREEN_SPACE_SHIP, GREEN_LASER)
    }

    def __init__(self, x, y, color, health=100):
        super().__init__(x, y, health)
        self.ship_img, self.laser_img = self.COLOR_MAP[color]
        self.mask = pygame.mask.from_surface(self.ship_img)

    def move(self, vel):
        self.y += vel

def collide(obj1, obj2):
    offset_x = obj2.x - obj1.x
    offset_y = obj2.y - obj1.y
    return obj1.mask.overlap(obj2.mask, (offset_x, offset_y)) != None 

def smooth_moment(hand_x, hand_y, prev_x, prev_y, smoothing_factor=0.8):
    smooth_x = int(smoothing_factor * prev_x + (1 - smoothing_factor) * hand_x)
    smooth_y = int(smoothing_factor * prev_y + (1 - smoothing_factor) * hand_y)
    return smooth_x, smooth_y

def main():
    global player_x, player_y, prev_hand_x, prev_hand_y
    run = True
    FPS = 60
    level = 0
    lives = 5
    main_font = pygame.font.SysFont("comicsans", 30)
    lost_font = pygame.font.SysFont("comicsans", 50)
    cap = cv2.VideoCapture(0)


    enemies = []
    wave_length = 5
    enemy_vel = 0.75

    player_vel = 5
    laser_vel = 5

    player = Player(300, 580)
    player_x, player_y = 300, 580 
    prev_hand_x, prev_hand_y = player_x, player_y

    clock = pygame.time.Clock()

    lost = False
    lost_count = 0

    def redraw_window():
        WIN.blit(BG, (0, 0))

        # draw text  
        lives_label = main_font.render(f"Lives: {lives}", 1, (255, 255, 255))
        level_label = main_font.render(f"Level: {level}", 1, (255, 255, 255))

        WIN.blit(lives_label, (10, 10))
        WIN.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))

        for enemy in enemies:
            enemy.draw(WIN)

        player.draw(WIN)

        if lost == True:
            lost_label = lost_font.render("You Lost!!", 1, (255, 0, 0))
            WIN.blit(lost_label, (WIDTH / 2 - lost_label.get_width() / 2, 
                                  HEIGHT / 2 - lost_label.get_height() / 2))

        pygame.display.update()

    while run:
        clock.tick(FPS)
        success, img = cap.read()
        if not success:
            break
        img = cv2.flip(img, 1)
        img = detector.findHands(img)
        lmList = detector.findPosition(img)

        # Display the hand tracking
        display_width = 320
        display_height = 240
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.resize(img, (display_width, display_height))

        cv2.imshow("Image", img)
        if len(lmList) != 0:
            hand_x = int(lmList[0][1] * (WIDTH / 650))
            hand_y = int(lmList[0][2] * (HEIGHT / 650))

            if abs(hand_x - prev_hand_x) > dead_zone or abs(hand_y - prev_hand_y) > dead_zone:
                player_x += (hand_x - prev_hand_x) * SENSITIVITY
                player_y += (hand_y - prev_hand_y) * SENSITIVITY

                player_x, player_y = smooth_moment(hand_x, hand_y, prev_hand_x, prev_hand_y)
                prev_hand_x, prev_hand_y = player_x, player_y
                player.x, player.y = player_x, player_y

            index_finger_x, index_finger_y = lmList[8][1], lmList[8][2]
            palm_x, palm_y = lmList[0][1], lmList[0][2]
            distance = ((index_finger_x - palm_x)**2 + (index_finger_y - palm_y)**2) ** 0.5

            # Shoot if the hand make a fist
            if distance < 100: 
                player.shoot()

        redraw_window()  

        if lives <= 0 or player.health <= 0:
            lost = True
            lost_count += 1

        if lost:
            if lost_count > FPS * 3:
                run = False
            else:
                continue

        if len(enemies) == 0:
            level += 1
            wave_length += 5
            for i in range(wave_length):
                enemy = Enemy(random.randrange(40, WIDTH - 80),
                              random.randrange(-int(750 * math.exp(level)), -100), 
                              random.choice(["red", "blue", "green"]))
                enemies.append(enemy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
        
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_a] or keys[pygame.K_LEFT]) and player.x - player_vel > 0: # left
            player.x -= player_vel
        if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) and player.x + player_vel + player.get_width() < WIDTH: # right
            player.x += player_vel
        if (keys[pygame.K_w] or keys[pygame.K_UP]) and player.y - player_vel > 0: # up
            player.y -= player_vel
        if (keys[pygame.K_s] or keys[pygame.K_DOWN]) and player.y + player_vel + player.get_height() + 10 < HEIGHT: # down
            player.y += player_vel  
        if (keys[pygame.K_SPACE]):
            player.shoot()

        for enemy in enemies[:]:
            enemy.move(enemy_vel)
            enemy.move_lasers(laser_vel, player)

            if random.randrange(0, 2 * 60) == 1:
                enemy.shoot()
            
            if collide(enemy, player):
                player.health -= 10
                enemies.remove(enemy)

            elif enemy.y + enemy.get_height() > HEIGHT:
                lives -= 1
                enemies.remove(enemy)
        
        player.move_lasers(-laser_vel, enemies)

def main_menu():
    title_font = pygame.font.SysFont("comicsans", 45)
    run = True

    while run:
        WIN.blit(BG, (0, 0))
        title_label = title_font.render("Press the mouse to begin...", 1, (255, 255, 255))
        WIN.blit(title_label, (WIDTH/2 - title_label.get_width()/2, HEIGHT/2 - title_label.get_height()/2))

        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run =  False
            if event.type == pygame.MOUSEBUTTONDOWN:
                main()

    pygame.quit()

main_menu()