# scripts/ecocash_scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
from config.scraper_config import SCRAPER_CONFIG

def scrape_faqs(url):
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    questions = []
    answers = []
    
    question_elements = soup.find_all(class_='question')
    for question_element in question_elements:
        question_text = question_element.get_text(strip=True)
        questions.append(question_text)
        
        answer_element = question_element.find_next_sibling(class_='answer')
        if answer_element:
            answer_text = ' '.join(p.get_text(strip=True) for p in answer_element.find_all('p'))
            answers.append(answer_text)
        else:
            answers.append('No answer found')
    
    return questions, answers

def main():
    config = SCRAPER_CONFIG['ecocash']
    questions, answers = scrape_faqs(config['url'])
    
    df = pd.DataFrame({
        'Question': questions,
        'Answer': answers
    })
    
    df.to_csv(config['output_file'], index=False)
    print(f"FAQ data has been successfully extracted and saved to '{config['output_file']}'")

if __name__ == "__main__":
    main()