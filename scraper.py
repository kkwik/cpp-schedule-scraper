from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm
import sys, os
import json
import re


# Disable print
def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restore print
def enablePrint():
    sys.stdout = sys.__stdout__

rex = re.compile(r'\s+') # Regex used to remove excess whitespace
# Function used to cleanup scraped text
def cleanupText(input):
	output = rex.sub(' ', input) # Remove multiple whitespaces
	output = output.replace('\u2013', '-') # Remove en dashes found in time
	output = output.strip() # Remove excess spaces
	return output

'''
Execution start
'''
arguments = sys.argv[1:]

tqdmDisabled = False
headless = True
for arg in arguments:
	if arg == '-q':	#Enable quiet execution. No prints no tqdm
		blockPrint()
		tqdmDisabled = True
	elif arg == '-s':	#Enable showing selenium window
		headless = False


'''
Stage 1 - Setup
'''
print('Starting driver...')
options = Options()
options.headless = headless
driver = webdriver.Firefox(options=options, executable_path=r'geckodriver.exe') #Need to provide geckodriver. Tested using geckodriver-v0.29.1-win64
driver.implicitly_wait(10)

print('Loading website...')
driver.get('https://schedule.cpp.edu')

print('Selecting term...')
element = driver.find_element_by_id('ctl00_ContentPlaceHolder1_TermDDL') # Choose term
element.click()
element = driver.find_element_by_css_selector('select#ctl00_ContentPlaceHolder1_TermDDL > option[value="2223"]')
element.click()


print('Getting subjects...')
element = driver.find_element_by_id('ctl00_ContentPlaceHolder1_Button1') #Find button that shows all subject abbreviations
element.click() #Click
element = driver.find_element_by_id('ctl00_ContentPlaceHolder1_GetSubjectCodesGV')	#Get the table that has all subject abbreviations
abbrevationElements = driver.find_elements_by_css_selector('table#ctl00_ContentPlaceHolder1_GetSubjectCodesGV > tbody > tr > td:nth-of-type(2)') #Get list of elements that contain abbreviation

subjectList = []	#List that will contain strings of abreviations i.e. [ABM, CS, ...]
for el in abbrevationElements:
	subjectList += [el.text]

'''
Stage 2 - Extract HTML from page
'''
print('Extracting courses...')
subjectCoursesHTML = [] # A list that contains the html for course offering tables
for subject in tqdm(subjectList, disable=tqdmDisabled):	#Go through every subject
	element = driver.find_element_by_id('ctl00_ContentPlaceHolder1_ClassSubject')	#Find input box and send subject abbreviation
	element.clear()
	element.send_keys(subject)
	
	element = driver.find_element_by_id('ctl00_ContentPlaceHolder1_SearchButton')	#Click search
	element.click()

	# If no courses are offered for the subject, skip. When there are courses offered this id tag == test
	if driver.find_element_by_css_selector('span#ctl00_ContentPlaceHolder1_ResultSet_LBL > h4').get_attribute('id') != 'test':
		continue

	subjectCourses = driver.find_elements_by_css_selector('div#class_list > ol > li')	#Get list of elements that contain the course info
	for course in subjectCourses:
		subjectCoursesHTML += [course.get_attribute('innerHTML')] # Get HTML from tables
driver.quit()	# No longer needed

'''
Stage 3 - Parse table HTML and transfer into dictionary
'''
print('Extracting content from HTML...')
courseList = []
for courseEntryHTML in tqdm(subjectCoursesHTML, disable=tqdmDisabled):
	parsed_html = BeautifulSoup(courseEntryHTML, features="html5lib")
	courseOffering = {}
	courseOffering['ClassTitle'] = cleanupText(parsed_html.find('span', attrs={'class':'ClassTitle'}).strong.text)
	courseOffering['Section'] = cleanupText(parsed_html.text).split(' Class Nbr')[0].split(' ', 2)[2]
	courseOffering['ClassNbr'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell13')}).text)
	courseOffering['Capacity'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell14')}).text)
	courseOffering['Title'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell8')}).text)
	courseOffering['Units'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell9')}).text)
	courseOffering['Time'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell1')}).text)
	courseOffering['BuildingRoom'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell2')}).text)
	courseOffering['Date'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell12')}).text)
	courseOffering['Session'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell17')}).text)
	courseOffering['Instructor'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell4')}).text)
	courseOffering['Mode'] = cleanupText(parsed_html.find('td', attrs={'id': lambda L: L and L.endswith('TableCell10')}).text)

	courseList += [courseOffering]

'''
Stage 4 - Convert dictionaries into json
'''
print('Writing to file...')
jsonCourseList = json.dumps(courseList)
with open('data.json', 'w') as outputFile:
	outputFile.write(jsonCourseList)

print('Complete.')