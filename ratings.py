import os
import statistics
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions() 
options.add_argument("start-maximized")
options.add_argument("--headless")
options.add_experimental_option('excludeSwitches', ['enable-logging'])
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

ratings_columns = ['Tournament', 'Date', 'Rating', 'Included']

def find_update_date(year, month):
    # Take the date as though it is at the 8th of next month
    d = datetime(year, month, 8)
    # Check if the 8th is a Tuesday (the 2nd in the month)
    if d.weekday() == 1:
        update_date = d
    # Deal with it being the Monday before the 2nd Tuesday
    elif d.weekday() == 0:
        offset = 1
        update_date = d + timedelta(offset)
    else:
        offset = 8 - d.weekday()
        update_date = d + timedelta(offset)
    return update_date
    

def get_evaluated_events(pdga_number):
    # Contain objects to store all of the retreived details
    evaluated_events = []
    ratings_frame = pd.DataFrame(columns=ratings_columns)
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
        ratings_frame.loc[len(ratings_frame)] = [tournament, date, int(round_rating), included]
    return evaluated_events, ratings_frame

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
            # Check that the tournament or event is a valid ratings event -> anything with an X is not rated
            tier = tournament.find_element(By.CLASS_NAME, 'tier')
            if 'X' not in tier.text:
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
    ratings_frame = pd.DataFrame(columns=ratings_columns)
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
                        ratings_frame.loc[len(ratings_frame)] = ['', date, int(rating.text), 'Yes']
    ratings_frame = ratings_frame.iloc[::-1]
    return ratings_frame

def calculate_ratings(ratings_table, current_rating):
    # Calculate the standard deviation of the rounds
    st_dev = ratings_table['Rating'].std()
    average_round = ratings_table['Rating'].mean()
    today = datetime.today()
    # Take the date as though it is at the 8th of next month
    update_date_yr_ago = find_update_date(today.year - 1, today.month)
    current_date_yr_ago = datetime(today.year - 1, today.month, today.day)
    # Check to see if we are past the update date of this month already
    if current_date_yr_ago > update_date_yr_ago:
        update_date_yr_ago = find_update_date(today.year - 1, today.month + 1)
    # Preprocess the list of ratings by converting the date strings into formal dates
    updated_ratings = pd.DataFrame(columns=ratings_columns)
    for i, row in ratings_table.iterrows():
        row['Date'] = datetime.strptime(row['Date'], '%d-%b-%Y')
        # Determine whether any rounds should be excluded -> outside 2.5 STDEV or 100 points of current rating
        if int(row['Rating']) > (average_round - 100) and int(row['Rating']) > (current_rating - 2.5*st_dev):
            # Also check the round was in the last 12 months
            if row['Date'] > update_date_yr_ago:
                row['Included'] = 'Yes'
                updated_ratings = pd.concat([updated_ratings, pd.DataFrame([row])])
            else:
                row['Included'] = 'No'
                updated_ratings = pd.concat([updated_ratings, pd.DataFrame([row])])
        else:
            row['Included'] = 'No'
            updated_ratings = pd.concat([updated_ratings, pd.DataFrame([row])])
    # Work out the total number of rounds and the number of rounds to double count due to recency
    recent_rounds = int(len(updated_ratings[updated_ratings['Included'] == 'Yes']) * 0.25)

    # Calculate and return the resultant average as the new rating and the change from current
    counted_rounds = 0
    ratings_sum = 0
    for i, row in updated_ratings.iterrows():
        if row['Included'] == 'Yes':
            counted_rounds += 1
            if i < recent_rounds:
                ratings_sum += int(row['Rating']) * 2
            else:
                ratings_sum += int(row['Rating'])
    return ratings_sum // (counted_rounds + recent_rounds), updated_ratings

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Predict your next PDGA rating update')
    parser.add_argument('pdga_number', type=str, help='PDGA number')
    parser.add_argument('--additional', nargs='+', help='Add additional rounds that are not read automatically')
    args = parser.parse_args()
    # Get the PDGA number passed through the command line
    pdga_number = args.pdga_number
    # # Retrieve a list of all the events this player has competed in (only concerned with the current year as the only reason we want the list is to add new rounds)
    all_events, event_lookup, current_rating = get_all_events(pdga_number)
    # Get a list of the currently evaluated events and the currently considered ratings
    evaluated_events, ratings_table = get_evaluated_events(pdga_number)
    # For any event not already included, retrieve the player ratings for the event
    for event in all_events:
        if event not in evaluated_events:
            # Get the link for the event page
            page = event_lookup[event]
            # Then add these ratings to the list of existent ratings
            new_ratings = get_round_ratings_from_tournament(pdga_number, page)
            new_ratings['Tournament'] = event
            ratings_table = pd.concat([new_ratings, ratings_table])
    ratings_table = ratings_table.reset_index(drop=True)
    # Then calculate the new rating based on the up to date list of round ratings
    if args.additional:
        # Create a new row to add to the DataFrame
        custom_rounds = pd.DataFrame(columns=ratings_table.columns)
        # Create a fake row
        template = {'Tournament': 'Custom', 'Date': datetime.strftime(datetime.today(), '%d-%b-%Y'), 'Rating': '', 'Included': 'Yes'}
        for round in args.additional:
            round_row = pd.DataFrame(template, index=[0])
            round_row['Rating'] = int(round)
            custom_rounds = pd.concat([round_row, custom_rounds])
        ratings_table = pd.concat([custom_rounds, ratings_table])
        ratings_table = ratings_table.reset_index(drop=True)
    driver.quit()
    new_rating, ratings_table = calculate_ratings(ratings_table, current_rating)
    print('Your new rating is estimated to be:', new_rating)
    print(ratings_table)
