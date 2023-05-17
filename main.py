# This part downloads all the libraries automatically to the computer.
required_packages = {'matplotlib', 'numpy', 'pygame'}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required_packages - installed
if missing:
    python = sys.executable
    subprocess.check_call([python, '-m', 'pip', 'install', *missing], stdout = subprocess.DEVNULL)


import matplotlib.pyplot as plt
import numpy as np
import pygame
from pygame.locals import *


#  **IMPORTANT** This variable defines the type of run (manual or automatic)
# if True - run automatically until less than 1% infected (and show graph)
# if False -
#    * display everything inside a window
#    * let the user run manually:
#       - move iterations by pressing the SPACE key
#       - display the graph for the current iteration pressing the G key
automatic = False

# Parameters
FAST_PROBABILITY = 0.2
STARTING_NUM_OF_SICK = 0.04
INFECTION_PROBABILITY = 0.1
SICKNESS_LENGTH = 15
INFECTION_MULTIPLIER = 5
AUTOMAT_SIZE = 200
NUM_OF_PEOPLE = 6000
INFECTION_THRESHOLD = 0.2 * NUM_OF_PEOPLE

# Sizes
ARR_SIZE = AUTOMAT_SIZE
SCREEN_SIZE = 600
RECT_SIZE = SCREEN_SIZE / ARR_SIZE

# Colors
EMPTY_COLOR = (255, 255, 255)
SICK_COLOR = (255, 0, 0)
HEALTHY_COLOR = (0, 150, 0)

MOVEMENTS = [(x, y) for x in range(-1, 2) for y in range(-1, 2)]

current_iteration = 0
num_of_infected_people = 0
history = []


# Utility functions
def chance(probability):
    sample = random.random()
    return sample < probability


def show_graph():
    global history
    iter = np.arange(1, len(history) + 1)
    plt.title(f'Infection history until iteration no. {len(history)}')
    infected_ratios = list(map(lambda infected_amount: infected_amount / NUM_OF_PEOPLE, history))
    plt.plot(iter, infected_ratios)
    plt.ylabel('infected ratio')
    plt.xlabel('iteration')
    plt.show()


class Map:
    def __init__(self, map_size, people):
        self.EMPTY = -1
        self.map_size = map_size
        self.people = people
        self.curr_surface = np.zeros((map_size, map_size)) - 1
        for i, person in enumerate(people, 0):
            x, y = person.position
            self.curr_surface[y, x] = i
        self.next_surface = np.copy(self.curr_surface)

    def has_infected_neighbor(self, person):
        x, y = person.position
        x_min = max(x - 1, 0)
        x_max = min(x + 1, self.map_size - 1)
        y_min = max(y - 1, 0)
        y_max = min(y + 1, self.map_size - 1)
        for i in range(y_min, y_max + 1):
            for j in range(x_min, x_max + 1):
                person_index = int(self.curr_surface[i, j])
                if person_index >= 0:
                    neighbor = self.people[person_index]
                    if not neighbor.is_healthy:
                        return True
        return False

    def in_bounds(self, point):
        x, y = point
        return 0 <= x and x < self.map_size and 0 <= y and y < self.map_size

    def is_occupied(self, point):
        if not self.in_bounds(point):
            return True
        x, y = point
        return self.curr_surface[y, x] != self.EMPTY or self.next_surface[y, x] != self.EMPTY

    # We handle collisions by using two different states: current iteration and next iteration
    # We allow a person to move to point P if and only if the P is unoccupied in the current iteration and the next iteration
    # This means that each person will always have the option to stay in his current position
    # When a person moves from point P - the next iteration's will be unoccupied, and the current will still be occupied
    def get_legal_movements(self, person):
        x, y = person.position
        movements = list(filter(lambda m: not self.is_occupied((x + m[0], y + m[1])), MOVEMENTS))
        return movements

    def move_person(self, person, movement):
        old_x, old_y = person.position
        new_x, new_y = old_x + movement[0], old_y + movement[1]
        self.next_surface[new_y, new_x] = self.next_surface[old_y, old_x]
        self.next_surface[old_y, old_x] = self.EMPTY
        person.position = (new_x, new_y)

    def next_iteration(self):
        self.curr_surface = np.copy(self.next_surface)


class Person:
    def __init__(self, position, is_fast=False, infection_probability=1):
        self.position = position
        self.is_fast = is_fast
        self.has_been_sick = False
        self.is_healthy = True
        self.infect(infection_probability)

    def infect(self, probability=1):
        global num_of_infected_people
        if chance(probability):
            self.has_been_sick = True
            self.sickness_countdown = SICKNESS_LENGTH
            self.is_healthy = False
            num_of_infected_people += 1

    def update(self, surface_map):
        if self.is_fast:
            for _ in range(10):
                self.inner_update(surface_map)
        else:
            self.inner_update(surface_map)

    def inner_update(self, surface_map):
        global num_of_infected_people
        if not self.has_been_sick:
            if surface_map.has_infected_neighbor(self):
                probability = INFECTION_PROBABILITY if num_of_infected_people > INFECTION_THRESHOLD else INFECTION_PROBABILITY * INFECTION_MULTIPLIER
                self.infect(probability)
        else:
            self.sickness_countdown -= 1
            if self.sickness_countdown == 0:
                self.is_healthy = True
                num_of_infected_people -= 1

        legal_movements = surface_map.get_legal_movements(self)
        # stay in the same place is there are no legal movements
        if len(legal_movements) > 0:
            movement = random.choice(legal_movements)
            surface_map.move_person(self, movement)

    def render(self, window):
        x, y = self.position
        rect = [x * RECT_SIZE, y * RECT_SIZE, RECT_SIZE, RECT_SIZE]
        color = HEALTHY_COLOR if self.is_healthy else SICK_COLOR
        pygame.draw.rect(window, color, rect, 0)


def init_persons(surface_size, num_of_people, infection_probability):
    points = [(x, y) for x in range(surface_size) for y in range(surface_size)]
    people_locations = random.sample(points, num_of_people)
    people = []
    for i in range(num_of_people):
        person = Person(
            position=people_locations[i],
            infection_probability=infection_probability,
            is_fast=chance(FAST_PROBABILITY)
        )
        people.append(person)
    return people


# initialize objects
persons = init_persons(
    surface_size=ARR_SIZE,
    num_of_people=NUM_OF_PEOPLE,
    infection_probability=STARTING_NUM_OF_SICK
)
surface_map = Map(ARR_SIZE, persons)


def apply_iteration():
    global current_iteration
    current_iteration += 1
    surface_map.next_iteration()
    history.append(num_of_infected_people)
    for person in persons:
        person.update(surface_map)


if automatic:
    while num_of_infected_people > 0.01 * NUM_OF_PEOPLE:
        print(f'iteration {current_iteration}: {num_of_infected_people}/{NUM_OF_PEOPLE}')
        apply_iteration()
    show_graph()
else:
    # initiate pygame and give permission to use pygame's functionality.
    pygame.init()
    # create the display surface object of specific dimension.
    window = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))

    # main loop
    run = True
    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                apply_iteration()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_g:
                show_graph()

        # Fill the scree with white color
        window.fill(EMPTY_COLOR)
        for person in persons:
            person.render(window)

        # render the new screen
        pygame.display.update()

    # finish and close window
    pygame.quit()
