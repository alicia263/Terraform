import os

# Base directory for output files
BASE_OUTPUT_DIR = os.environ.get('SCRAPER_OUTPUT_DIR', 'data')

SCRAPER_CONFIG = {
    'ecosure': {
        'url': 'https://www.ecosure.co.zw/faqs',
        'output_file': os.path.join(BASE_OUTPUT_DIR, 'ecosure_faq_zw_data.csv'),
        'scraper_type': 'class_based',
        'question_class': 'q',
        'answer_class': 'a'
    },
    'ecocash': {
        'url': 'https://www.ecocash.co.zw/faqs',
        'output_file': os.path.join(BASE_OUTPUT_DIR, 'ecocash_faq_data.csv'),
        'scraper_type': 'class_based',
        'question_class': 'question',
        'answer_class': 'answer'
    },
    'econet': {
        'url': 'https://www.econet.co.zw/faq',
        'output_file': os.path.join(BASE_OUTPUT_DIR, 'Econet_FAQ.csv'),
        'scraper_type': 'container_based',
        'container_class': 'faq-accordion',
        'question_class': 'faq-title',
        'answer_class': 'faq-content'
    }
}

# Configuration for CSV combiner
CSV_COMBINER_CONFIG = {
    'input_files': [config['output_file'] for config in SCRAPER_CONFIG.values()],
    'output_file': os.path.join(BASE_OUTPUT_DIR, 'merge_csv_data.csv')
}

# Add any global settings here
GLOBAL_SETTINGS = {
    'request_timeout': 30,  # in seconds
    'max_retries': 3,
    'retry_delay': 5  # in seconds
}