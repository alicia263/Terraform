# scripts/econet_scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
from config.scraper_config import SCRAPER_CONFIG

def scrape_page(url):
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    questions = []
    answers = []
    
    faq_containers = soup.find_all('div', class_='faq-accordion')
    
    for container in faq_containers:
        faq_items = container.find_all('div', class_='faq-main')
        
        for item in faq_items:
            question_div = item.find('div', class_='faq-title')
            question = question_div.find('h4').text.strip() if question_div else 'No question found'
            
            answer_div = item.find('div', class_='faq-content')
            answer = answer_div.find('p').text.strip() if answer_div else 'No answer found'
            
            questions.append(question)
            answers.append(answer)
    
    return questions, answers

def main():
    config = SCRAPER_CONFIG['econet']
    questions, answers = scrape_page(config['url'])
    
    df = pd.DataFrame({
        'Question': questions,
        'Answer': answers
    })
    
    df.to_csv(config['output_file'], index=False)
    print(f"FAQ data has been successfully extracted and saved to '{config['output_file']}'")

if __name__ == "__main__":
    main()