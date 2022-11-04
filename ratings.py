from concurrent.futures import process
import os
import statistics
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions() 
options.add_argument("start-maximized")
options.add_experimental_option('excludeSwitches', ['enable-logging'])
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def get_evaluated_events(pdga_number):
    # Contain objects to store all of the retreived details
    evaluated_events = []
    round_ratings = []
    # Retrieve the ratings details page
    driver.get("https://www.pdga.com/player/{}/details".format(pdga_number))

    # Get the all rows from the table of ratings
    ratings_table = driver.find_element(By.TAG_NAME, 'tbody')
    ratings = ratings_table.find_elements(By.TAG_NAME, 'tr')

    # For each row, strip the name of the event, the rating, the date, the included and the evaluated column
    for rating in ratings:
        # Get the name of the event
        tournament = rating.find_element(By.CLASS_NAME, 'tournament').text
        # Get the date
        date = rating.find_element(By.CLASS_NAME, 'date').text
        # If the date is split across a period, take the end date
        if 'to' in date:
            date = date.split(' to ')[1]
        # Get the rating
        round_rating = rating.find_element(By.CLASS_NAME, 'round-rating').text
        # Get the included
        included = rating.find_element(By.CLASS_NAME, 'included').text
        # Add this to the necessary objects
        # Add the tuple of (event, date) to the evaluated_events list
        if tournament not in evaluated_events:
            evaluated_events.append(tournament)
        # Add the tuple of (date, rating) to the round ratings list where included == 'Yes'
        if included == 'Yes':
            round_ratings.append((round_rating, date))

    return evaluated_events, round_ratings[::-1]

def get_all_events(pdga_number):
    # Create objects to store all events
    event_lookup = dict()
    # Retrieve the ratings details page
    driver.get("https://www.pdga.com/player/{}".format(pdga_number))
    # Get each table including tournament results
    tables = driver.find_elements(By.TAG_NAME, 'tbody')
    # Ignore the top table including divisional points
    for table in tables[1:]:
        # For each table, retrieve each row
        tournaments = table.find_elements(By.TAG_NAME, 'tr')
        for tournament in tournaments:
            # Retrieve the tournament name and the link to the tournament page
            event = tournament.find_element(By.CLASS_NAME, 'tournament')
            name = event.text
            link = event.find_element(By.TAG_NAME, 'a').get_attribute('href')
            event_lookup[name] = link
    # Also get the current PDGA rating
    rating = driver.find_element(By.CLASS_NAME, 'current-rating').text[16:].split(' ')[0]
    return list(event_lookup.keys()), event_lookup, int(rating)


def get_round_ratings_from_tournament(pdga_number, page):
    # Create the object to return
    new_rounds = []
    # Get the event results page
    driver.get(page)
    # Find the tournament date (for the rounds)
    date = driver.find_element(By.CLASS_NAME, 'tournament-date').text[6:]
    if 'to' in date:
            date = date.split(' to ')[1]

    # Toggle round ratings button
    driver.implicitly_wait(2)
    show_ratings_button = driver.find_element(By.CLASS_NAME, 'tour-show-round-ratings-link')
    show_ratings_button.click()

    # Find all tables
    tables = driver.find_elements(By.TAG_NAME, 'tbody')
    for table in tables[1:]:
        players = table.find_elements(By.TAG_NAME, 'tr')
        # For each player
        for player in players:
            # Get the player's PDGA number
            player_pdga = player.find_element(By.CLASS_NAME, 'pdga-number').text 
            # If the numbers match
            if player_pdga == pdga_number:
                # Get all the round rating elements
                player_ratings = player.find_elements(By.CLASS_NAME, 'round-rating')
                for rating in player_ratings:
                    if rating.text:
                        new_rounds.append((rating.text, date))
    return new_rounds

def calculate_ratings(ratings, current_rating):
    # Create a processed object
    processed_ratings = []
    counted_rounds = []
    ratings_sum = 0

    # Preprocess the list of ratings by converting the date strings into formal dates
    for rating in ratings:
        rating_date = datetime.strptime(rating[1], '%d-%b-%Y')
        processed_ratings.append((rating[0], rating_date))
    ratings = [int(x[0]) for x in processed_ratings]
    
    # Calculate the standard deviation of the rounds
    st_dev = statistics.pstdev(ratings)
    average_round = statistics.mean(ratings)
    today = datetime.today()
    date_1yr_ago = datetime(today.year-1, today.month, today.day)

    for round in processed_ratings:
        # Determine whether any rounds should be excluded -> outside 2.5 STDEV or 100 points of current rating
        if int(round[0]) > (average_round - 100) and int(round[0]) > (current_rating - 2.5*st_dev):
            # Also check the round was in the last 12 months
            if round[1] > date_1yr_ago:
                counted_rounds.append(round)


    # Order the rounds correctly
    counted_rounds = counted_rounds[::-1]

    # Work out the total number of rounds and the number of rounds to double count due to recency
    recent_rounds = int(len(counted_rounds) * 0.25)

    # Calculate and return the resultant average as the new rating and the change from current
    for i in range(len(counted_rounds)):
        if i < recent_rounds:
            ratings_sum += int(counted_rounds[i][0]) * 2
        else:
            ratings_sum += int(counted_rounds[i][0])
    return ratings_sum // (len(counted_rounds) + recent_rounds)

if __name__ == '__main__':
    # Get the PDGA number passed through the command line
    pdga_number = sys.argv[1]
    # # Retrieve a list of all the events this player has competed in (only conerned with the current year as the only reason we want the list is to add new rounds)
    all_events, event_lookup, current_rating = get_all_events(pdga_number)
    # Get a list of the currently evaluated events and the currently considered ratings
    evaluated_events, round_ratings = get_evaluated_events(pdga_number)
    # For any event not already included, retrieve the player ratings for the event
    for event in all_events:
        if event not in evaluated_events:
            # Get the link for the event page
            page = event_lookup[event]
            # Then add these ratings to the list of existent ratings
            round_ratings.extend(get_round_ratings_from_tournament(pdga_number, page))
    # Then calculate the new rating based on the up to date list of round ratings
    new_rating = calculate_ratings(round_ratings, current_rating)
    print('Your new rating is estimated to be:', new_rating)
