from concurrent.futures import process
import os
import statistics
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

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

    return evaluated_events, round_ratings

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
    return list(event_lookup.keys()), event_lookup


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

def calculate_ratings(ratings):
    # Create a processed object
    processed_ratings = []

    # Get the current rating

    # Preprocess the list of ratings by converting the date strings into formal dates
    for rating in ratings:
        rating_date = datetime.strptime(rating[1], '%d-%b-%Y')
        processed_ratings.append((rating[0], rating_date))
    ratings = [int(x[0]) for x in processed_ratings]
    
    # Calculate the standard deviation of the rounds
    st_dev = statistics.pstdev(ratings)
    
    # Determine whether any rounds should be excluded -> outside 2.5 STDEV or 100 points of current rating
    for round in processed_ratings:
        if round[0]:
            pass

    # Order the list by dates desc

    # Work out the total number of rounds and the number of rounds to double count due to recency

    # Calculate and return the resultant average as the new rating and the change from current

    pass


if __name__ == '__main__':
    # Get the PDGA number passed through the command line
    pdga_number = sys.argv[1]
    # # Retrieve a list of all the events this player has competed in (only conerned with the current year as the only reason we want the list is to add new rounds)
    # all_events, event_lookup = get_all_events(pdga_number)
    # # Get a list of the currently evaluated events and the currently considered ratings
    # evaluated_events, round_ratings = get_evaluated_events(pdga_number)
    # # For any event not already included, retrieve the player ratings for the event
    # for event in all_events:
    #     if event not in evaluated_events:
    #         # Get the link for the event page
    #         page = event_lookup[event]
    #         # Then add these ratings to the list of existent ratings
    #         round_ratings.extend(get_round_ratings_from_tournament(pdga_number, page))
    round_ratings = [('861', '3-Oct-2022'), ('861', '3-Oct-2022'), ('854', '3-Oct-2022'), ('804', '11-Sep-2022'), ('872', '11-Sep-2022'), ('860', '21-Aug-2022'), ('879', '21-Aug-2022'), ('860', '21-Aug-2022'), ('863', '7-Aug-2022'), ('885', '7-Aug-2022'), ('819', '31-Jul-2022'), ('859', 
'31-Jul-2022'), ('759', '22-May-2022'), ('792', '22-May-2022'), ('777', '14-Apr-2022'), ('789', '14-Apr-2022'), ('871', '14-Apr-2022'), ('761', '15-Oct-2022'), ('856', '15-Oct-2022'), ('882', '22-Oct-2022'), ('820', '22-Oct-2022'), ('861', '30-Oct-2022'), ('897', '01-Nov-2022'), ('880', '01-Nov-2022')]
    # Then calculate the new rating based on the up to date list of round ratings
    new_rating = calculate_ratings(round_ratings)
    print(new_rating)
